import json
import random
from collections import defaultdict
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

    annotations_by_image: Dict[int, List[Dict]] = defaultdict(list)
    for ann in data.get("annotations", []):
        image_id = int(ann["image_id"])
        if image_id in images:
            annotations_by_image[image_id].append(ann)

    categories: Dict[int, str] = {}
    for cat in data.get("categories", []):
        categories[int(cat["id"])] = str(cat["name"])

    return CocoIndex(
        images=images,
        annotations_by_image=dict(annotations_by_image),
        categories=categories,
    )


def split_image_ids(
    image_ids: Sequence[int],
    val_ratio: float,
    seed: int,
) -> Tuple[List[int], List[int]]:
    if not image_ids:
        return [], []

    if val_ratio <= 0 or val_ratio >= 1:
        raise ValueError("val_ratio must be in range (0, 1)")

    ids = list(image_ids)
    rnd = random.Random(seed)
    rnd.shuffle(ids)

    n_total = len(ids)
    n_val = max(1, int(round(n_total * val_ratio)))
    n_val = min(n_val, n_total - 1) if n_total > 1 else 0

    val_ids = ids[:n_val]
    train_ids = ids[n_val:]

    if not train_ids and val_ids:
        train_ids = [val_ids.pop()]

    return train_ids, val_ids


def find_missing_images(
    images_dir: Path,
    index: CocoIndex,
) -> List[str]:
    base = Path(images_dir)
    missing: List[str] = []
    for rec in index.images.values():
        image_path = base / rec.file_name
        if not image_path.exists():
            missing.append(rec.file_name)
    return missing


def _build_mask_from_polygons(
    annotations: Sequence[Dict],
    height: int,
    width: int,
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)

    for ann in annotations:
        segmentation = ann.get("segmentation")
        if not isinstance(segmentation, list):
            # Skip RLE or malformed segmentation in this simplified pipeline.
            continue

        for polygon in segmentation:
            if not isinstance(polygon, list) or len(polygon) < 6:
                continue

            pts = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
            pts = np.round(pts).astype(np.int32)
            if pts.shape[0] >= 3:
                cv2.fillPoly(mask, [pts], color=1)

    return mask


class CocoPolygonSegmentationDataset(Dataset):
    def __init__(
        self,
        index: CocoIndex,
        image_ids: Sequence[int],
        images_dir: Path,
        image_size: Optional[Tuple[int, int]] = None,
        augment: bool = False,
    ) -> None:
        self.index = index
        self.image_ids = list(image_ids)
        self.images_dir = Path(images_dir)
        self.image_size = image_size
        self.augment = augment

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
        mask = _build_mask_from_polygons(anns, height=rec.height, width=rec.width)

        if self.image_size is not None:
            target_w, target_h = self.image_size
            image = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            mask = cv2.resize(mask, (target_w, target_h), interpolation=cv2.INTER_NEAREST)

        if self.augment and random.random() < 0.5:
            image = np.ascontiguousarray(image[:, ::-1, :])
            mask = np.ascontiguousarray(mask[:, ::-1])

        image = image.astype(np.float32) / 255.0
        image = np.transpose(image, (2, 0, 1))
        mask = mask.astype(np.float32)[None, :, :]

        image_t = torch.from_numpy(image)
        mask_t = torch.from_numpy(mask)

        return image_t, mask_t
