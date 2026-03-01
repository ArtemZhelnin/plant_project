from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from inference.postprocessing import (
    estimate_metrics_from_multiclass_mask,
    image_to_data_uri,
    make_multiclass_overlay_image,
)


@dataclass(frozen=True)
class LoadedYoloModel:
    model: object
    device: str
    class_names: List[str]


def _normalize_name(name: str) -> str:
    return str(name).strip().lower()


def _map_yolo_name_to_target_class(name: str) -> Optional[int]:
    n = _normalize_name(name)
    if "leaf" in n:
        return 1
    if "root" in n:
        return 2
    if "stem" in n:
        return 3
    return None


def load_yolo_segmentation_model(weights_path: Path, device: str = "auto") -> LoadedYoloModel:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ImportError(
            "ultralytics is not installed. Install dependencies with: "
            "py -3.11 -m pip install -r backend/requirements.txt"
        ) from exc

    w = Path(weights_path)
    if not w.exists():
        raise FileNotFoundError(f"YOLO checkpoint not found: {w}")

    model = YOLO(str(w))
    names_obj = getattr(model, "names", {})
    class_names: List[str]
    if isinstance(names_obj, dict):
        class_names = [str(names_obj[k]) for k in sorted(names_obj.keys())]
    elif isinstance(names_obj, list):
        class_names = [str(x) for x in names_obj]
    else:
        class_names = []

    return LoadedYoloModel(
        model=model,
        device=device,
        class_names=class_names,
    )


def _resolve_yolo_device(device: str) -> str:
    if device == "auto":
        try:
            import torch

            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"
    return device


def _compose_multiclass_mask_from_instances(
    masks_data: np.ndarray,
    classes: np.ndarray,
    scores: np.ndarray,
    class_names: List[str],
    image_shape: Tuple[int, int],
) -> np.ndarray:
    h, w = image_shape
    class_mask = np.zeros((h, w), dtype=np.uint8)
    score_map = np.full((h, w), -1.0, dtype=np.float32)

    for i in range(masks_data.shape[0]):
        cls_idx = int(classes[i])
        score = float(scores[i]) if i < scores.shape[0] else 0.0

        if cls_idx < 0 or cls_idx >= len(class_names):
            continue
        target_cls = _map_yolo_name_to_target_class(class_names[cls_idx])
        if target_cls is None:
            continue

        mask_i = masks_data[i]
        if mask_i.shape != (h, w):
            mask_i = cv2.resize(mask_i.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
        mask_bin = mask_i > 0.5
        if not np.any(mask_bin):
            continue

        update = mask_bin & (score >= score_map)
        class_mask[update] = np.uint8(target_cls)
        score_map[update] = score

    return class_mask


def predict_plant_yolo(
    image_rgb: np.ndarray,
    bundle: LoadedYoloModel,
    mm_per_pixel: Optional[float] = None,
    conf_threshold: float = 0.15,
) -> Dict[str, object]:
    dev = _resolve_yolo_device(bundle.device)
    results = bundle.model.predict(
        source=image_rgb,
        verbose=False,
        device=dev,
        conf=float(conf_threshold),
        retina_masks=True,
    )
    if not results:
        empty_mask = np.zeros(image_rgb.shape[:2], dtype=np.uint8)
        overlay = make_multiclass_overlay_image(image_rgb=image_rgb, mask_classes=empty_mask)
        metrics = estimate_metrics_from_multiclass_mask(mask_classes=empty_mask, mm_per_pixel=mm_per_pixel)
        return {
            "metrics": metrics,
            "overlay": image_to_data_uri(overlay),
            "confidence": 0.0,
            "mask": empty_mask,
            "class_names": ["background", "leaf", "root", "stem"],
        }

    r = results[0]
    h, w = image_rgb.shape[:2]
    class_mask = np.zeros((h, w), dtype=np.uint8)

    masks = getattr(r, "masks", None)
    boxes = getattr(r, "boxes", None)
    if masks is not None and boxes is not None and getattr(masks, "data", None) is not None:
        masks_np = masks.data.detach().cpu().numpy().astype(np.float32)
        cls_np = boxes.cls.detach().cpu().numpy().astype(np.int64) if getattr(boxes, "cls", None) is not None else np.array([], dtype=np.int64)
        conf_np = boxes.conf.detach().cpu().numpy().astype(np.float32) if getattr(boxes, "conf", None) is not None else np.array([], dtype=np.float32)
        class_mask = _compose_multiclass_mask_from_instances(
            masks_data=masks_np,
            classes=cls_np,
            scores=conf_np,
            class_names=bundle.class_names,
            image_shape=(h, w),
        )

        valid_scores = conf_np[np.isfinite(conf_np)]
        confidence = float(np.mean(valid_scores)) if valid_scores.size > 0 else 0.0
    else:
        confidence = 0.0

    overlay = make_multiclass_overlay_image(image_rgb=image_rgb, mask_classes=class_mask)
    metrics = estimate_metrics_from_multiclass_mask(mask_classes=class_mask, mm_per_pixel=mm_per_pixel)

    return {
        "metrics": metrics,
        "overlay": image_to_data_uri(overlay),
        "confidence": confidence,
        "mask": class_mask,
        "class_names": ["background", "leaf", "root", "stem"],
    }
