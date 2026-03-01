import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple

from calibration.detect_corners import ChessboardDetection


@dataclass(frozen=True)
class ScaleResult:
    pixel_mean: float
    pixel_std: float
    mm_per_pixel: float
    n_samples: int


def _neighbor_distances(
    corners: np.ndarray,
    pattern_size: Tuple[int, int],
) -> np.ndarray:
    """Compute distances between horizontally/vertically adjacent corners."""
    cols, rows = pattern_size
    grid = corners.reshape(rows, cols, 2)

    dists: List[float] = []

    # horizontal neighbors
    for r in range(rows):
        for c in range(cols - 1):
            p0 = grid[r, c]
            p1 = grid[r, c + 1]
            dists.append(float(np.linalg.norm(p1 - p0)))

    # vertical neighbors
    for r in range(rows - 1):
        for c in range(cols):
            p0 = grid[r, c]
            p1 = grid[r + 1, c]
            dists.append(float(np.linalg.norm(p1 - p0)))

    return np.asarray(dists, dtype=np.float64)


def compute_mm_per_pixel(
    detection: ChessboardDetection,
    square_size_mm: float,
) -> ScaleResult:
    """Compute mm_per_pixel for a detection.

    Strategy:
        pixel_mean = mean distance between adjacent inner corners (px)
        mm_per_pixel = square_size_mm / pixel_mean
    """
    dists = _neighbor_distances(detection.corners, detection.pattern_size)
    if dists.size == 0:
        raise ValueError("No neighbor distances computed")

    pixel_mean = float(np.mean(dists))
    pixel_std = float(np.std(dists, ddof=1)) if dists.size > 1 else 0.0

    if pixel_mean <= 0:
        raise ValueError("Invalid mean pixel distance")

    mm_per_pixel = float(square_size_mm / pixel_mean)

    return ScaleResult(
        pixel_mean=pixel_mean,
        pixel_std=pixel_std,
        mm_per_pixel=mm_per_pixel,
        n_samples=int(dists.size),
    )


def to_dict(res: ScaleResult) -> Dict[str, float]:
    return {
        "pixel_mean": res.pixel_mean,
        "pixel_std": res.pixel_std,
        "mm_per_pixel": res.mm_per_pixel,
        "n_samples": res.n_samples,
    }
