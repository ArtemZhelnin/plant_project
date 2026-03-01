import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset


@dataclass(frozen=True)
class CocoImageRecord:
    image_id: int
    file_name: str
    width: int
    height: int


@dataclass(frozen=True)
class CocoIndex:
    images: Dict[int, CocoImageRecord]
    annotations_by_image: Dict[int, List[Dict]]
    categories: Dict[int, str]


def load_coco_index(annotation_path: Path) -> CocoIndex:
    with Path(annotation_path).open("r", encoding="utf-8") as f:
        data = json.load(f)

    images: Dict[int, CocoImageRecord] = {}
    for img in data.get("images", []):
        image_id = int(img["id"])
        images[image_id] = CocoImageRecord(
            image_id=image_id,
            file_name=str(img["file_name"]),
            width=int(img["width"]),
            height=int(img["height"]),
        )

    annotations_by_image: Dict[int, List[Dict]] = {}
    for image_id in images:
        annotations_by_image[image_id] = []
    for ann in data.get("annotations", []):
        image_id = int(ann["image_id"])
        if image_id in images:
            annotations_by_image[image_id].append(ann)

    categories: Dict[int, str] = {}
    for cat in data.get("categories", []):
        categories[int(cat["id"])] = str(cat["name"])

    return CocoIndex(
        images=images,
        annotations_by_image=annotations_by_image,
        categories=categories,
    )


def _normalize_name(name: str) -> str:
    return name.strip().lower()


def build_class_mapping(categories: Dict[int, str]) -> Dict[int, int]:
    """
    Map raw COCO category ids to training class ids:
    0=background, 1=leaf, 2=root, 3=stem.
    """
    name_to_class = {
        "leaf": 1,
        "root": 2,
        "stem": 3,
    }
    mapping: Dict[int, int] = {}
    for cat_id, cat_name in categories.items():
        target = name_to_class.get(_normalize_name(cat_name))
        if target is not None:
            mapping[int(cat_id)] = int(target)
    required = {"leaf", "root", "stem"}
    present = {_normalize_name(n) for n in categories.values()}
    missing = sorted(required.difference(present))
    if missing:
        raise ValueError(f"Missing required classes in COCO categories: {missing}")
    return mapping


def _default_class_priority() -> Dict[int, int]:
    # Resolve polygon overlaps deterministically.
    # Higher number means higher priority.
    return {
        0: 0,  # background
        1: 1,  # leaf
        3: 2,  # stem
        2: 3,  # root
    }


def _build_multiclass_mask(
    annotations: Sequence[Dict],
    height: int,
    width: int,
    category_to_class: Dict[int, int],
    class_priority: Optional[Dict[int, int]] = None,
) -> np.ndarray:
    if class_priority is None:
        class_priority = _default_class_priority()

    mask = np.zeros((height, width), dtype=np.uint8)
    prio = np.full((height, width), -1, dtype=np.int16)

    for ann in annotations:
        raw_cat_id = int(ann.get("category_id", -1))
        cls = category_to_class.get(raw_cat_id)
        if cls is None:
            continue

        segmentation = ann.get("segmentation")
        if not isinstance(segmentation, list):
            continue

        poly_mask = np.zeros((height, width), dtype=np.uint8)
        for polygon in segmentation:
            if not isinstance(polygon, list) or len(polygon) < 6:
                continue
            pts = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
            pts = np.round(pts).astype(np.int32)
            if pts.shape[0] >= 3:
                cv2.fillPoly(poly_mask, [pts], color=1)

        if not np.any(poly_mask):
            continue

        cls_prio = int(class_priority.get(cls, 1))
        update = (poly_mask == 1) & (cls_prio >= prio)
        mask[update] = cls
        prio[update] = cls_prio

    return mask


def _apply_augmentations(
    image: np.ndarray,
    mask: np.ndarray,
    rng: random.Random,
) -> Tuple[np.ndarray, np.ndarray]:
    if rng.random() < 0.5:
        image = np.ascontiguousarray(image[:, ::-1, :])
        mask = np.ascontiguousarray(mask[:, ::-1])

    if rng.random() < 0.2:
        image = np.ascontiguousarray(image[::-1, :, :])
        mask = np.ascontiguousarray(mask[::-1, :])

    if rng.random() < 0.35:
        rot_code = rng.choice([cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE])
        image = cv2.rotate(image, rot_code)
        mask = cv2.rotate(mask, rot_code)

    if rng.random() < 0.45:
        alpha = rng.uniform(0.8, 1.25)   # contrast
        beta = rng.uniform(-20.0, 20.0)  # brightness
        image = np.clip(image.astype(np.float32) * alpha + beta, 0.0, 255.0).astype(np.uint8)

    if rng.random() < 0.25:
        gamma = rng.uniform(0.85, 1.2)
        lut = np.array(
            [((i / 255.0) ** gamma) * 255.0 for i in range(256)],
            dtype=np.float32,
        )
        image = cv2.LUT(image, np.clip(lut, 0, 255).astype(np.uint8))

    if rng.random() < 0.2:
        k = rng.choice([3, 5])
        image = cv2.GaussianBlur(image, (k, k), sigmaX=0)

    if rng.random() < 0.2:
        sigma = rng.uniform(2.0, 8.0)
        noise = np.random.normal(0.0, sigma, image.shape).astype(np.float32)
        image = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    return image, mask


class CocoSplitMulticlassDataset(Dataset):
    def __init__(
        self,
        images_dir: Path,
        annotation_path: Path,
        image_size: Optional[Tuple[int, int]] = None,
        augment: bool = False,
        seed: int = 42,
    ) -> None:
        self.images_dir = Path(images_dir)
        self.annotation_path = Path(annotation_path)
        self.image_size = image_size
        self.augment = augment
        self._rng = random.Random(seed)

        self.index = load_coco_index(self.annotation_path)
        self.category_to_class = build_class_mapping(self.index.categories)
        self.image_ids = sorted(self.index.images.keys())

        missing = [
            rec.file_name
            for rec in self.index.images.values()
            if not (self.images_dir / rec.file_name).exists()
        ]
        if missing:
            preview = ", ".join(missing[:5])
            raise FileNotFoundError(
                f"{len(missing)} image files from annotations are missing in {self.images_dir}. "
                f"Examples: {preview}"
            )

    def __len__(self) -> int:
        return len(self.image_ids)

    def __getitem__(self, idx: int):
        image_id = self.image_ids[idx]
        rec = self.index.images[image_id]
        anns = self.index.annotations_by_image.get(image_id, [])

        image_path = self.images_dir / rec.file_name
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        mask = _build_multiclass_mask(
            annotations=anns,
            height=rec.height,
            width=rec.width,
            category_to_class=self.category_to_class,
        )

        if self.augment:
            image, mask = _apply_augmentations(image, mask, rng=self._rng)

        if self.image_size is not None:
            target_w, target_h = self.image_size
            image = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            mask = cv2.resize(mask, (target_w, target_h), interpolation=cv2.INTER_NEAREST)

        image = image.astype(np.float32) / 255.0
        image = np.transpose(image, (2, 0, 1))
        mask = mask.astype(np.int64)

        return torch.from_numpy(image), torch.from_numpy(mask)

    def count_class_pixels(self) -> np.ndarray:
        counts = np.zeros(4, dtype=np.int64)
        for image_id in self.image_ids:
            rec = self.index.images[image_id]
            anns = self.index.annotations_by_image.get(image_id, [])
            mask = _build_multiclass_mask(
                annotations=anns,
                height=rec.height,
                width=rec.width,
                category_to_class=self.category_to_class,
            )
            binc = np.bincount(mask.reshape(-1), minlength=4)
            counts += binc[:4]
        return counts
