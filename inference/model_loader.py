from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    num_classes: int
    class_names: List[str]


def resolve_device(device: str = "auto") -> torch.device:
    if device != "auto":
        return torch.device(device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _extract_training_args(ckpt: Dict[str, Any]) -> Dict[str, Any]:
    args = ckpt.get("args", {})
    if isinstance(args, dict):
        return args
    return {}


def _default_class_names(num_classes: int) -> List[str]:
    if num_classes == 1:
        return ["plant"]
    if num_classes == 4:
        return ["background", "leaf", "root", "stem"]
    return [f"class_{i}" for i in range(num_classes)]


def _infer_num_classes(state_dict: Dict[str, Any], checkpoint: Dict[str, Any], train_args: Dict[str, Any]) -> int:
    class_names = checkpoint.get("class_names")
    if isinstance(class_names, list) and class_names:
        return int(len(class_names))

    arg_classes = train_args.get("num_classes")
    if arg_classes is not None:
        try:
            return int(arg_classes)
        except (TypeError, ValueError):
            pass

    for k, v in state_dict.items():
        if (
            isinstance(k, str)
            and "segmentation_head" in k
            and isinstance(v, torch.Tensor)
            and v.ndim == 4
        ):
            out_ch = int(v.shape[0])
            if out_ch > 0:
                return out_ch

    return 1


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
    num_classes = _infer_num_classes(state_dict=state_dict, checkpoint=checkpoint, train_args=train_args)
    raw_class_names = checkpoint.get("class_names")
    if isinstance(raw_class_names, list) and len(raw_class_names) == num_classes:
        class_names = [str(x) for x in raw_class_names]
    else:
        class_names = _default_class_names(num_classes)

    model = build_segmentation_model(
        architecture=architecture,
        encoder_name=encoder,
        encoder_weights=None,
        in_channels=3,
        classes=num_classes,
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
        num_classes=num_classes,
        class_names=class_names,
    )
