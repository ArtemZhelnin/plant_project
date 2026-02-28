import json
from pathlib import Path
from typing import Dict, Union


DEFAULT_CALIBRATION_PATH = Path("calibration/results.json")


def load_calibration_config(
    path: Union[str, Path] = DEFAULT_CALIBRATION_PATH,
) -> Dict[str, Union[float, int]]:
    """Load finalized calibration values from calibration/results.json."""
    calibration_path = Path(path)
    if not calibration_path.exists():
        raise FileNotFoundError(f"Calibration file not found: {calibration_path}")

    with calibration_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    required = ("mm_per_pixel", "std", "relative_std", "images_used")
    missing = [k for k in required if k not in data]
    if missing:
        raise KeyError(f"Missing required calibration keys: {missing}")

    return {
        "mm_per_pixel": float(data["mm_per_pixel"]),
        "std": float(data["std"]),
        "relative_std": float(data["relative_std"]),
        "images_used": int(data["images_used"]),
    }


def get_mm_per_pixel(path: Union[str, Path] = DEFAULT_CALIBRATION_PATH) -> float:
    """Shortcut for measurements code: mm_per_pixel = get_mm_per_pixel()."""
    return load_calibration_config(path)["mm_per_pixel"]
