import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ChessboardDetection:
    image_size: Tuple[int, int]
    pattern_size: Tuple[int, int]
    corners: np.ndarray  # shape: (N, 2)


def detect_chessboard_corners(
    image_bgr: np.ndarray,
    pattern_size: Tuple[int, int],
) -> Optional[ChessboardDetection]:
    """Detect inner corners of a chessboard.

    Args:
        image_bgr: OpenCV image in BGR format.
        pattern_size: (cols, rows) == (number of inner corners per row, per col)

    Returns:
        ChessboardDetection if found, else None.
    """
    if image_bgr is None or image_bgr.size == 0:
        return None

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    flags = (
        cv2.CALIB_CB_ADAPTIVE_THRESH
        | cv2.CALIB_CB_NORMALIZE_IMAGE
        | cv2.CALIB_CB_FAST_CHECK
    )

    found, corners = cv2.findChessboardCorners(gray, pattern_size, flags)
    if not found or corners is None:
        return None

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    corners_xy = corners.reshape(-1, 2).astype(np.float64)
    h, w = gray.shape[:2]

    return ChessboardDetection(
        image_size=(w, h),
        pattern_size=pattern_size,
        corners=corners_xy,
    )
