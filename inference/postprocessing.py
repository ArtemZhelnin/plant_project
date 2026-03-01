import base64
from io import BytesIO
from typing import Dict, Mapping, Optional

import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize


BACKGROUND_CLASS_ID = 0
LEAF_CLASS_ID = 1
ROOT_CLASS_ID = 2
STEM_CLASS_ID = 3

# RGB colors
CLASS_COLORS: Dict[int, tuple[int, int, int]] = {
    LEAF_CLASS_ID: (63, 208, 122),   # leaf: green
    ROOT_CLASS_ID: (235, 85, 165),   # root: magenta
    STEM_CLASS_ID: (255, 162, 64),   # stem: orange
}


def make_overlay_image(
    image_rgb: np.ndarray,
    mask_binary: np.ndarray,
    alpha: float = 0.55,
) -> np.ndarray:
    return make_multiclass_overlay_image(
        image_rgb=image_rgb,
        mask_classes=(mask_binary > 0).astype(np.uint8),
        alpha=alpha,
        class_colors={1: (255, 64, 160)},
    )


def make_multiclass_overlay_image(
    image_rgb: np.ndarray,
    mask_classes: np.ndarray,
    alpha: float = 0.55,
    class_colors: Optional[Mapping[int, tuple[int, int, int]]] = None,
) -> np.ndarray:
    if image_rgb.shape[:2] != mask_classes.shape[:2]:
        raise ValueError("Image and mask shapes do not match")

    colors = dict(CLASS_COLORS if class_colors is None else class_colors)
    mask = mask_classes.astype(np.uint8)

    base = image_rgb.astype(np.float32)
    result = (base * 0.32).astype(np.float32)

    fg = mask > BACKGROUND_CLASS_ID
    result[fg] = base[fg]

    for class_id, color in colors.items():
        class_mask = mask == int(class_id)
        if not np.any(class_mask):
            continue
        tint = np.array(color, dtype=np.float32)
        result[class_mask] = result[class_mask] * (1.0 - alpha) + tint * alpha

    out = np.clip(result, 0, 255).astype(np.uint8)

    for class_id, color in colors.items():
        class_mask = (mask == int(class_id)).astype(np.uint8) * 255
        if class_mask.max() == 0:
            continue
        contours, _ = cv2.findContours(class_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, contours, contourIdx=-1, color=tuple(int(c) for c in color), thickness=2)

    return out


def image_to_data_uri(image_rgb: np.ndarray) -> str:
    pil_img = Image.fromarray(image_rgb)
    buff = BytesIO()
    pil_img.save(buff, format="PNG")
    encoded = base64.b64encode(buff.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _skeleton_length_px(binary_mask: np.ndarray) -> float:
    if binary_mask.ndim != 2:
        raise ValueError("binary_mask must be 2D")

    mask_bool = binary_mask > 0
    if not np.any(mask_bool):
        return 0.0

    skel = skeletonize(mask_bool)
    if not np.any(skel):
        return 0.0

    s = skel.astype(bool)
    orth = (
        np.count_nonzero(s[:, :-1] & s[:, 1:])
        + np.count_nonzero(s[:-1, :] & s[1:, :])
    )
    diag = (
        np.count_nonzero(s[:-1, :-1] & s[1:, 1:])
        + np.count_nonzero(s[:-1, 1:] & s[1:, :-1])
    )
    return float(orth + diag * np.sqrt(2.0))


def estimate_metrics_from_mask(
    mask_binary: np.ndarray,
    mm_per_pixel: Optional[float] = None,
) -> Dict[str, float]:
    if mask_binary.ndim != 2:
        raise ValueError("mask_binary must be 2D")

    mm = float(mm_per_pixel) if mm_per_pixel is not None else 1.0
    ys, xs = np.where(mask_binary > 0)
    area_px = int(mask_binary.sum())

    if ys.size == 0 or xs.size == 0:
        return {
            "root_length_mm": 0.0,
            "stem_length_mm": 0.0,
            "leaf_area_mm2": 0.0,
            "root_area_mm2": 0.0,
            "stem_area_mm2": 0.0,
        }

    width_px = float(xs.max() - xs.min() + 1)
    height_px = float(ys.max() - ys.min() + 1)

    leaf_area_mm2 = float(area_px * (mm ** 2))
    stem_length_mm = float(height_px * mm)
    root_length_mm = float(width_px * mm)

    # Single-class plant segmentation: root area is unavailable separately.
    root_area_mm2 = 0.0

    return {
        "root_length_mm": root_length_mm,
        "stem_length_mm": stem_length_mm,
        "leaf_area_mm2": leaf_area_mm2,
        "root_area_mm2": root_area_mm2,
        "stem_area_mm2": 0.0,
    }


def estimate_metrics_from_multiclass_mask(
    mask_classes: np.ndarray,
    mm_per_pixel: Optional[float] = None,
) -> Dict[str, float]:
    if mask_classes.ndim != 2:
        raise ValueError("mask_classes must be 2D")

    mm = float(mm_per_pixel) if mm_per_pixel is not None else 1.0
    px2_to_mm2 = mm * mm

    leaf_mask = mask_classes == LEAF_CLASS_ID
    root_mask = mask_classes == ROOT_CLASS_ID
    stem_mask = mask_classes == STEM_CLASS_ID

    leaf_area_mm2 = float(np.count_nonzero(leaf_mask) * px2_to_mm2)
    root_area_mm2 = float(np.count_nonzero(root_mask) * px2_to_mm2)
    stem_area_mm2 = float(np.count_nonzero(stem_mask) * px2_to_mm2)

    root_length_mm = float(_skeleton_length_px(root_mask.astype(np.uint8)) * mm)
    stem_length_mm = float(_skeleton_length_px(stem_mask.astype(np.uint8)) * mm)

    return {
        "root_length_mm": root_length_mm,
        "stem_length_mm": stem_length_mm,
        "leaf_area_mm2": leaf_area_mm2,
        "root_area_mm2": root_area_mm2,
        "stem_area_mm2": stem_area_mm2,
    }
