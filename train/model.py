from typing import Optional

import torch.nn as nn


def build_segmentation_model(
    architecture: str = "unet",
    encoder_name: str = "resnet34",
    encoder_weights: Optional[str] = "imagenet",
    in_channels: int = 3,
    classes: int = 1,
) -> nn.Module:
    try:
        import segmentation_models_pytorch as smp
    except ImportError as exc:
        raise ImportError(
            "Failed to import segmentation_models_pytorch and its dependencies. "
            "Install dependencies with `py -3.11 -m pip install -r backend/requirements.txt` "
            f"and ensure extra deps are present (original error: {exc})."
        ) from exc

    arch = architecture.lower()

    if arch == "unet":
        return smp.Unet(
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=in_channels,
            classes=classes,
        )

    if arch == "fpn":
        return smp.FPN(
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=in_channels,
            classes=classes,
        )

    if arch in {"deeplabv3plus", "deeplabv3+"}:
        return smp.DeepLabV3Plus(
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=in_channels,
            classes=classes,
        )

    raise ValueError(
        "Unsupported architecture. Use one of: unet, fpn, deeplabv3plus"
    )
