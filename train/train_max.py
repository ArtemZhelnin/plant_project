import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.cuda.amp import GradScaler, autocast
from torch.optim import AdamW
from torch.optim.lr_scheduler import OneCycleLR
from torch.utils.data import DataLoader

from train.model import build_segmentation_model
from train.multiclass_dataset import CocoSplitMulticlassDataset
from train.multiclass_loss import CrossEntropyDiceLoss
from train.multiclass_metrics import compute_multiclass_metrics


NUM_CLASSES = 4
CLASS_NAMES = ["background", "leaf", "root", "stem"]


@dataclass
class EpochMetrics:
    loss: float
    miou_fg: float
    mdice_fg: float
    per_class_iou: List[float]
    per_class_dice: List[float]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Train high-quality multiclass plant segmentation")
    p.add_argument("--data_root", type=Path, default=Path("training"))
    p.add_argument("--output_dir", type=Path, default=Path("weights/segmentation_multiclass"))
    p.add_argument("--annotations_name", type=str, default="_annotations.coco.json")
    p.add_argument("--image_size", type=int, default=768)
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--batch_size", type=int, default=2)
    p.add_argument("--num_workers", type=int, default=0)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight_decay", type=float, default=1e-4)
    p.add_argument("--grad_clip", type=float, default=1.0)
    p.add_argument("--patience", type=int, default=24)
    p.add_argument("--architecture", default="deeplabv3plus", choices=["unet", "fpn", "deeplabv3plus"])
    p.add_argument("--encoder", default="resnet50")
    p.add_argument("--encoder_weights", default="imagenet", help="imagenet or none")
    p.add_argument("--device", default="auto", help="auto | cuda | cpu")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--tta_val", action="store_true", help="Use flip TTA in val/test")
    p.add_argument("--max_train_images", type=int, default=0, help="debug option; 0 means all")
    p.add_argument("--resume", type=Path, default=None, help="Path to checkpoint (best.pt/last.pt) to resume")
    p.add_argument("--freeze_bn", action="store_true", help="Force BatchNorm layers to eval mode during training")
    return p.parse_args()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def resolve_device(device_arg: str) -> torch.device:
    if device_arg != "auto":
        return torch.device(device_arg)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _compute_class_weights(pixel_counts: np.ndarray) -> torch.Tensor:
    counts = pixel_counts.astype(np.float64)
    total = np.maximum(counts.sum(), 1.0)
    freq = counts / total
    weights = 1.0 / np.sqrt(freq + 1e-8)

    # Background dominates area; downweight it to improve thin-structure quality.
    weights[0] = weights[0] * 0.35
    weights = weights / np.mean(weights)
    return torch.tensor(weights, dtype=torch.float32)


def _forward_with_tta(model: torch.nn.Module, images: torch.Tensor, use_tta: bool) -> torch.Tensor:
    logits = model(images)
    if not use_tta:
        return logits

    h = torch.flip(images, dims=[3])
    v = torch.flip(images, dims=[2])

    logits_h = torch.flip(model(h), dims=[3])
    logits_v = torch.flip(model(v), dims=[2])

    return (logits + logits_h + logits_v) / 3.0


def _set_batchnorm_eval(model: torch.nn.Module) -> None:
    for module in model.modules():
        if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
            module.eval()


def run_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: torch.nn.Module,
    device: torch.device,
    optimizer: Optional[torch.optim.Optimizer],
    scaler: Optional[GradScaler],
    scheduler: Optional[OneCycleLR],
    grad_clip: float,
    tta_eval: bool = False,
    freeze_bn: bool = False,
) -> EpochMetrics:
    is_train = optimizer is not None
    model.train(is_train)
    if is_train and freeze_bn:
        _set_batchnorm_eval(model)

    total_loss = 0.0
    total_miou = 0.0
    total_mdice = 0.0
    total_samples = 0
    total_iou_by_cls = np.zeros(NUM_CLASSES, dtype=np.float64)
    total_dice_by_cls = np.zeros(NUM_CLASSES, dtype=np.float64)

    use_amp = bool(device.type == "cuda")

    for images, masks in loader:
        images = images.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)
        batch_size = images.size(0)

        if is_train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(is_train):
            with autocast(enabled=use_amp):
                logits = _forward_with_tta(model, images, use_tta=(tta_eval and not is_train))
                loss = criterion(logits, masks)

            if is_train:
                if scaler is not None and use_amp:
                    scaler.scale(loss).backward()
                    if grad_clip > 0:
                        scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    if grad_clip > 0:
                        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                    optimizer.step()

                if scheduler is not None:
                    scheduler.step()

        with torch.no_grad():
            m = compute_multiclass_metrics(logits, masks, num_classes=NUM_CLASSES)

        total_loss += float(loss.item()) * batch_size
        total_miou += float(m["miou_fg"]) * batch_size
        total_mdice += float(m["mdice_fg"]) * batch_size
        total_samples += batch_size

        per_iou = np.array(m["per_class_iou"], dtype=np.float64)
        per_dice = np.array(m["per_class_dice"], dtype=np.float64)
        per_iou = np.nan_to_num(per_iou, nan=0.0)
        per_dice = np.nan_to_num(per_dice, nan=0.0)
        total_iou_by_cls += per_iou * batch_size
        total_dice_by_cls += per_dice * batch_size

    if total_samples == 0:
        return EpochMetrics(
            loss=0.0,
            miou_fg=0.0,
            mdice_fg=0.0,
            per_class_iou=[0.0] * NUM_CLASSES,
            per_class_dice=[0.0] * NUM_CLASSES,
        )

    return EpochMetrics(
        loss=total_loss / total_samples,
        miou_fg=total_miou / total_samples,
        mdice_fg=total_mdice / total_samples,
        per_class_iou=(total_iou_by_cls / total_samples).tolist(),
        per_class_dice=(total_dice_by_cls / total_samples).tolist(),
    )


def _build_split_dataset(
    data_root: Path,
    split_name: str,
    annotations_name: str,
    image_size: int,
    augment: bool,
    seed: int,
) -> CocoSplitMulticlassDataset:
    split_dir = data_root / split_name
    ann = split_dir / annotations_name
    if not split_dir.exists():
        raise FileNotFoundError(f"Split dir not found: {split_dir}")
    if not ann.exists():
        raise FileNotFoundError(f"COCO annotations not found: {ann}")

    return CocoSplitMulticlassDataset(
        images_dir=split_dir,
        annotation_path=ann,
        image_size=(image_size, image_size),
        augment=augment,
        seed=seed,
    )


def _fmt_cls_metrics(name: str, values: List[float]) -> str:
    parts = []
    for cls_name, val in zip(CLASS_NAMES, values):
        parts.append(f"{cls_name}:{val:.4f}")
    return f"{name}[{', '.join(parts)}]"


def main() -> None:
    args = parse_args()
    seed_everything(args.seed)

    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_ds = _build_split_dataset(
        data_root=data_root,
        split_name="train",
        annotations_name=args.annotations_name,
        image_size=args.image_size,
        augment=True,
        seed=args.seed,
    )
    val_ds = _build_split_dataset(
        data_root=data_root,
        split_name="valid",
        annotations_name=args.annotations_name,
        image_size=args.image_size,
        augment=False,
        seed=args.seed,
    )

    test_ds = None
    test_dir = data_root / "test"
    if test_dir.exists() and (test_dir / args.annotations_name).exists():
        test_ds = _build_split_dataset(
            data_root=data_root,
            split_name="test",
            annotations_name=args.annotations_name,
            image_size=args.image_size,
            augment=False,
            seed=args.seed,
        )

    if args.max_train_images > 0:
        train_ds.image_ids = train_ds.image_ids[: args.max_train_images]

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    test_loader = None
    if test_ds is not None:
        test_loader = DataLoader(
            test_ds,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            pin_memory=torch.cuda.is_available(),
        )

    device = resolve_device(args.device)
    encoder_weights = None if str(args.encoder_weights).lower() == "none" else args.encoder_weights
    model = build_segmentation_model(
        architecture=args.architecture,
        encoder_name=args.encoder,
        encoder_weights=encoder_weights,
        in_channels=3,
        classes=NUM_CLASSES,
    ).to(device)

    class_counts = train_ds.count_class_pixels()
    class_weights = _compute_class_weights(class_counts).to(device)

    criterion = CrossEntropyDiceLoss(
        num_classes=NUM_CLASSES,
        ce_weight=0.6,
        dice_weight=0.4,
        class_weights=class_weights,
    )
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    steps_per_epoch = max(1, len(train_loader))
    scheduler = OneCycleLR(
        optimizer,
        max_lr=args.lr,
        steps_per_epoch=steps_per_epoch,
        epochs=args.epochs,
        pct_start=0.15,
        anneal_strategy="cos",
        div_factor=10.0,
        final_div_factor=100.0,
    )
    scaler = GradScaler(enabled=(device.type == "cuda"))

    history: List[Dict[str, object]] = []
    best_val_miou = -1.0
    best_epoch = -1
    no_improve = 0
    start_epoch = 1

    if args.resume is not None:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            raise FileNotFoundError(f"Resume checkpoint not found: {resume_path}")
        resume_ckpt = torch.load(resume_path, map_location=device)
        model.load_state_dict(resume_ckpt["model_state_dict"], strict=True)
        if "optimizer_state_dict" in resume_ckpt and resume_ckpt["optimizer_state_dict"] is not None:
            optimizer.load_state_dict(resume_ckpt["optimizer_state_dict"])
        if (
            "scaler_state_dict" in resume_ckpt
            and resume_ckpt["scaler_state_dict"] is not None
            and scaler is not None
        ):
            scaler.load_state_dict(resume_ckpt["scaler_state_dict"])
        start_epoch = int(resume_ckpt.get("epoch", 0)) + 1
        best_val_miou = float(resume_ckpt.get("best_val_miou_fg", best_val_miou))
        best_epoch = int(resume_ckpt.get("best_epoch", best_epoch))
        if isinstance(resume_ckpt.get("history"), list):
            history = list(resume_ckpt["history"])

        print(f"Resumed from checkpoint: {resume_path}")
        print(f"Resume start epoch: {start_epoch} | best_val_miou_fg={best_val_miou:.4f}")

    print("=== Training configuration ===")
    print(f"data_root: {data_root}")
    print(f"output_dir: {output_dir}")
    print(f"device: {device}")
    print(f"train/val/test: {len(train_ds)} / {len(val_ds)} / {len(test_ds) if test_ds is not None else 0}")
    print(f"model: {args.architecture} / {args.encoder}")
    print(f"image_size: {args.image_size} | batch_size: {args.batch_size} | epochs: {args.epochs}")
    print(f"freeze_bn: {bool(args.freeze_bn or args.batch_size < 2)}")
    print(f"class pixel counts: {class_counts.tolist()}")
    print(f"class weights: {[round(float(x), 4) for x in class_weights.tolist()]}")

    for epoch in range(start_epoch, args.epochs + 1):
        train_metrics = run_epoch(
            model=model,
            loader=train_loader,
            criterion=criterion,
            device=device,
            optimizer=optimizer,
            scaler=scaler,
            scheduler=scheduler,
            grad_clip=args.grad_clip,
            tta_eval=False,
            freeze_bn=(args.freeze_bn or args.batch_size < 2),
        )
        val_metrics = run_epoch(
            model=model,
            loader=val_loader,
            criterion=criterion,
            device=device,
            optimizer=None,
            scaler=None,
            scheduler=None,
            grad_clip=0.0,
            tta_eval=args.tta_val,
            freeze_bn=False,
        )

        current_lr = float(optimizer.param_groups[0]["lr"])
        row = {
            "epoch": epoch,
            "lr": current_lr,
            "train": asdict(train_metrics),
            "val": asdict(val_metrics),
        }
        history.append(row)

        print(
            f"Epoch {epoch:03d}/{args.epochs} "
            f"| train_loss={train_metrics.loss:.4f} val_loss={val_metrics.loss:.4f} "
            f"| train_mIoU_fg={train_metrics.miou_fg:.4f} val_mIoU_fg={val_metrics.miou_fg:.4f} "
            f"| val_mDice_fg={val_metrics.mdice_fg:.4f} lr={current_lr:.2e}"
        )
        print("  " + _fmt_cls_metrics("val_iou", val_metrics.per_class_iou))
        print("  " + _fmt_cls_metrics("val_dice", val_metrics.per_class_dice))

        improved = val_metrics.miou_fg > best_val_miou
        if improved:
            best_val_miou = val_metrics.miou_fg
            best_epoch = epoch
            no_improve = 0
        else:
            no_improve += 1

        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scaler_state_dict": scaler.state_dict() if scaler is not None else None,
            "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
            "metrics": row,
            "args": vars(args),
            "class_names": CLASS_NAMES,
            "class_weights": [float(x) for x in class_weights.detach().cpu().tolist()],
            "best_val_miou_fg": float(best_val_miou),
            "best_epoch": int(best_epoch),
            "history": history,
        }
        torch.save(checkpoint, output_dir / "last.pt")

        if improved:
            torch.save(checkpoint, output_dir / "best.pt")
            print(f"  Saved new best.pt (val_mIoU_fg={best_val_miou:.4f})")

        if no_improve >= args.patience:
            print(f"Early stopping at epoch {epoch}: no val mIoU improvement for {args.patience} epochs.")
            break

    final_summary: Dict[str, object] = {
        "best_val_miou_fg": float(best_val_miou),
        "best_epoch": int(best_epoch),
        "train_images": len(train_ds),
        "val_images": len(val_ds),
        "test_images": len(test_ds) if test_ds is not None else 0,
        "class_names": CLASS_NAMES,
        "class_pixel_counts": class_counts.tolist(),
        "class_weights": [float(x) for x in class_weights.detach().cpu().tolist()],
        "history": history,
    }

    if (output_dir / "best.pt").exists() and test_loader is not None:
        print("Running final test evaluation with best.pt ...")
        ckpt = torch.load(output_dir / "best.pt", map_location=device)
        model.load_state_dict(ckpt["model_state_dict"], strict=True)
        model.eval()
        test_metrics = run_epoch(
            model=model,
            loader=test_loader,
            criterion=criterion,
            device=device,
            optimizer=None,
            scaler=None,
            scheduler=None,
            grad_clip=0.0,
            tta_eval=args.tta_val,
            freeze_bn=False,
        )
        final_summary["test"] = asdict(test_metrics)
        print(
            f"Test: loss={test_metrics.loss:.4f} "
            f"mIoU_fg={test_metrics.miou_fg:.4f} mDice_fg={test_metrics.mdice_fg:.4f}"
        )
        print("  " + _fmt_cls_metrics("test_iou", test_metrics.per_class_iou))
        print("  " + _fmt_cls_metrics("test_dice", test_metrics.per_class_dice))

    with (output_dir / "training_summary.json").open("w", encoding="utf-8") as f:
        json.dump(final_summary, f, ensure_ascii=False, indent=2)

    print(f"Finished. Best val mIoU_fg={best_val_miou:.4f} at epoch {best_epoch}")
    print(f"Artifacts saved to: {output_dir}")


if __name__ == "__main__":
    main()
