import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Union


DEFAULT_CALIBRATION_PATH = Path("calibration/results.json")
DEFAULT_ANNOTATIONS_PATH = Path("annotations/instances_default.json")
DEFAULT_IMAGES_DIR = Path("data/rukola")
DEFAULT_TRAIN_OUTPUT_DIR = Path("weights/segmentation")
DEFAULT_IMAGE_SIZE = 512
DEFAULT_BATCH_SIZE = 2
DEFAULT_EPOCHS = 30
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_VAL_RATIO = 0.2
DEFAULT_SEED = 42


@dataclass(frozen=True)
class TrainingConfig:
    annotations_path: Path = DEFAULT_ANNOTATIONS_PATH
    images_dir: Path = DEFAULT_IMAGES_DIR
    output_dir: Path = DEFAULT_TRAIN_OUTPUT_DIR
    image_size: int = DEFAULT_IMAGE_SIZE
    batch_size: int = DEFAULT_BATCH_SIZE
    epochs: int = DEFAULT_EPOCHS
    learning_rate: float = DEFAULT_LEARNING_RATE
    val_ratio: float = DEFAULT_VAL_RATIO
    seed: int = DEFAULT_SEED


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


def get_training_config() -> TrainingConfig:
    return TrainingConfig()
