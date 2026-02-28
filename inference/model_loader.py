from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import torch

from train.model import build_segmentation_model


@dataclass(frozen=True)
class LoadedSegmentationModel:
    model: torch.nn.Module
    device: torch.device
    image_size: int
    architecture: str
    encoder: str
    threshold: float


def resolve_device(device: str = "auto") -> torch.device:
    if device != "auto":
        return torch.device(device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _extract_training_args(ckpt: Dict[str, Any]) -> Dict[str, Any]:
    args = ckpt.get("args", {})
    if isinstance(args, dict):
        return args
    return {}


def load_segmentation_model(
    weights_path: Path,
    device: str = "auto",
    threshold: float = 0.5,
) -> LoadedSegmentationModel:
    ckpt_path = Path(weights_path)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {ckpt_path}")

    dev = resolve_device(device)
    checkpoint = torch.load(ckpt_path, map_location=dev)

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
        train_args = _extract_training_args(checkpoint)
    elif isinstance(checkpoint, dict):
        state_dict = checkpoint
        train_args = {}
    else:
        raise ValueError("Unsupported checkpoint format")

    architecture = str(train_args.get("architecture", "unet"))
    encoder = str(train_args.get("encoder", "resnet34"))
    image_size = int(train_args.get("image_size", 512))

    model = build_segmentation_model(
        architecture=architecture,
        encoder_name=encoder,
        encoder_weights=None,
        in_channels=3,
        classes=1,
    )
    model.load_state_dict(state_dict, strict=True)
    model.to(dev)
    model.eval()

    return LoadedSegmentationModel(
        model=model,
        device=dev,
        image_size=image_size,
        architecture=architecture,
        encoder=encoder,
        threshold=float(threshold),
    )
