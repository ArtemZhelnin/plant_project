from typing import Tuple

import cv2
import numpy as np
import torch


def preprocess_image(
    image_rgb: np.ndarray,
    image_size: int,
) -> Tuple[torch.Tensor, Tuple[int, int]]:
    if image_rgb is None or image_rgb.size == 0:
        raise ValueError("Input image is empty")

    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("Expected RGB image with shape HxWx3")

    h, w = image_rgb.shape[:2]
    resized = cv2.resize(image_rgb, (image_size, image_size), interpolation=cv2.INTER_LINEAR)
    x = resized.astype(np.float32) / 255.0
    x = np.transpose(x, (2, 0, 1))
    x = np.expand_dims(x, axis=0)
    x_t = torch.from_numpy(x)
    return x_t, (h, w)
