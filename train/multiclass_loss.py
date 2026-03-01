from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def multiclass_soft_dice_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    num_classes: int,
    class_weights: Optional[torch.Tensor] = None,
    smooth: float = 1.0,
    ignore_index: int = -100,
) -> torch.Tensor:
    probs = torch.softmax(logits, dim=1)

    valid_mask = targets != ignore_index
    safe_targets = torch.where(valid_mask, targets, torch.zeros_like(targets))

    one_hot = F.one_hot(safe_targets, num_classes=num_classes).permute(0, 3, 1, 2).float()
    valid_mask_4d = valid_mask.unsqueeze(1).float()
    one_hot = one_hot * valid_mask_4d
    probs = probs * valid_mask_4d

    dims = (0, 2, 3)
    intersection = torch.sum(probs * one_hot, dim=dims)
    cardinality = torch.sum(probs + one_hot, dim=dims)
    dice = (2.0 * intersection + smooth) / (cardinality + smooth)

    if class_weights is not None:
        w = class_weights.to(logits.device).float()
        w = w / torch.clamp(w.sum(), min=1e-6)
        dice_loss = 1.0 - torch.sum(dice * w)
    else:
        dice_loss = 1.0 - dice.mean()
    return dice_loss


class CrossEntropyDiceLoss(nn.Module):
    def __init__(
        self,
        num_classes: int,
        ce_weight: float = 0.6,
        dice_weight: float = 0.4,
        class_weights: Optional[torch.Tensor] = None,
        ignore_index: int = -100,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.ce_weight = float(ce_weight)
        self.dice_weight = float(dice_weight)
        self.ignore_index = int(ignore_index)
        self.register_buffer(
            "class_weights",
            class_weights.float() if class_weights is not None else torch.tensor([]),
            persistent=False,
        )

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_w = self.class_weights if self.class_weights.numel() > 0 else None
        ce = F.cross_entropy(
            logits,
            targets,
            weight=ce_w,
            ignore_index=self.ignore_index,
        )
        dice = multiclass_soft_dice_loss(
            logits=logits,
            targets=targets,
            num_classes=self.num_classes,
            class_weights=ce_w,
            ignore_index=self.ignore_index,
        )
        return self.ce_weight * ce + self.dice_weight * dice
