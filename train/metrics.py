import torch


@torch.no_grad()
def dice_score(
    logits: torch.Tensor,
    targets: torch.Tensor,
    threshold: float = 0.5,
    eps: float = 1e-7,
) -> float:
    probs = torch.sigmoid(logits)
    preds = (probs >= threshold).float()

    dims = (1, 2, 3)
    intersection = torch.sum(preds * targets, dim=dims)
    denom = torch.sum(preds, dim=dims) + torch.sum(targets, dim=dims)

    dice = (2.0 * intersection + eps) / (denom + eps)
    return float(dice.mean().item())


@torch.no_grad()
def iou_score(
    logits: torch.Tensor,
    targets: torch.Tensor,
    threshold: float = 0.5,
    eps: float = 1e-7,
) -> float:
    probs = torch.sigmoid(logits)
    preds = (probs >= threshold).float()

    dims = (1, 2, 3)
    intersection = torch.sum(preds * targets, dim=dims)
    union = torch.sum((preds + targets) > 0, dim=dims).float()

    iou = (intersection + eps) / (union + eps)
    return float(iou.mean().item())
