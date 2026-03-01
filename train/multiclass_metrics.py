from typing import Dict, List

import torch


@torch.no_grad()
def compute_multiclass_metrics(
    logits: torch.Tensor,
    targets: torch.Tensor,
    num_classes: int,
    ignore_index: int = -100,
) -> Dict[str, object]:
    preds = torch.argmax(logits, dim=1)
    valid = targets != ignore_index

    per_class_iou: List[float] = []
    per_class_dice: List[float] = []

    for cls in range(num_classes):
        pred_c = (preds == cls) & valid
        targ_c = (targets == cls) & valid

        intersection = torch.sum(pred_c & targ_c).float()
        union = torch.sum(pred_c | targ_c).float()
        denom_dice = torch.sum(pred_c).float() + torch.sum(targ_c).float()

        iou = (intersection / union).item() if union > 0 else float("nan")
        dice = ((2.0 * intersection) / denom_dice).item() if denom_dice > 0 else float("nan")
        per_class_iou.append(iou)
        per_class_dice.append(dice)

    fg_iou = [x for i, x in enumerate(per_class_iou) if i > 0 and x == x]
    fg_dice = [x for i, x in enumerate(per_class_dice) if i > 0 and x == x]

    return {
        "per_class_iou": per_class_iou,
        "per_class_dice": per_class_dice,
        "miou_fg": float(sum(fg_iou) / len(fg_iou)) if fg_iou else 0.0,
        "mdice_fg": float(sum(fg_dice) / len(fg_dice)) if fg_dice else 0.0,
    }
