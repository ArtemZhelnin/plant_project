import base64
from io import BytesIO
from typing import Dict, Optional

import cv2
import numpy as np
from PIL import Image


def make_overlay_image(
    image_rgb: np.ndarray,
    mask_binary: np.ndarray,
    alpha: float = 0.55,
) -> np.ndarray:
    if image_rgb.shape[:2] != mask_binary.shape[:2]:
        raise ValueError("Image and mask shapes do not match")

    mask = (mask_binary > 0).astype(np.uint8)

    base = image_rgb.astype(np.float32)
    result = (base * 0.35).astype(np.float32)  # dim background
    result[mask == 1] = base[mask == 1]        # keep original colors inside mask

    tint = np.zeros_like(result)
    tint[:, :, 0] = 255.0  # red
    tint[:, :, 2] = 128.0  # blue -> magenta
    result[mask == 1] = result[mask == 1] * (1.0 - alpha) + tint[mask == 1] * alpha

    out = np.clip(result, 0, 255).astype(np.uint8)

    contours, _ = cv2.findContours(
        (mask * 255).astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    cv2.drawContours(out, contours, contourIdx=-1, color=(255, 255, 0), thickness=2)

    return out


def image_to_data_uri(image_rgb: np.ndarray) -> str:
    pil_img = Image.fromarray(image_rgb)
    buff = BytesIO()
    pil_img.save(buff, format="PNG")
    encoded = base64.b64encode(buff.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def estimate_metrics_from_mask(
    mask_binary: np.ndarray,
    mm_per_pixel: Optional[float] = None,
) -> Dict[str, float]:
    ys, xs = np.where(mask_binary > 0)
    area_px = int(mask_binary.sum())

    if ys.size == 0 or xs.size == 0:
        return {
            "root_length_mm": 0.0,
            "stem_length_mm": 0.0,
            "leaf_area_mm2": 0.0,
            "root_area_mm2": 0.0,
        }

    width_px = float(xs.max() - xs.min() + 1)
    height_px = float(ys.max() - ys.min() + 1)

    if mm_per_pixel is None:
        mm_per_pixel = 1.0

    leaf_area_mm2 = float(area_px * (mm_per_pixel ** 2))
    stem_length_mm = float(height_px * mm_per_pixel)
    root_length_mm = float(width_px * mm_per_pixel)

    # Single-class plant segmentation: root area is unavailable separately.
    root_area_mm2 = 0.0

    return {
        "root_length_mm": root_length_mm,
        "stem_length_mm": stem_length_mm,
        "leaf_area_mm2": leaf_area_mm2,
        "root_area_mm2": root_area_mm2,
    }
