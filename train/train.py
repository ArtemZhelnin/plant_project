import argparse
import json
import random
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import numpy as np
    import torch
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import ReduceLROnPlateau
    from torch.utils.data import DataLoader
except ImportError as exc:
    raise SystemExit(
        "Missing training dependencies. "
        "Install them with: py -3.11 -m pip install -r backend/requirements.txt"
    ) from exc

from train.config import (
    DEFAULT_ANNOTATIONS_PATH,
    DEFAULT_BATCH_SIZE,
    DEFAULT_EPOCHS,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_IMAGES_DIR,
    DEFAULT_LEARNING_RATE,
    DEFAULT_SEED,
    DEFAULT_TRAIN_OUTPUT_DIR,
    DEFAULT_VAL_RATIO,
)
from train.dataset import (
    CocoPolygonSegmentationDataset,
    find_missing_images,
    load_coco_index,
    split_image_ids,
)
from train.loss import BCEDiceLoss
from train.metrics import dice_score, iou_score
from train.model import build_segmentation_model


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def resolve_device(device_arg: str) -> torch.device:
    if device_arg != "auto":
        return torch.device(device_arg)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def run_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: torch.nn.Module,
    device: torch.device,
    optimizer: Optional[torch.optim.Optimizer] = None,
) -> Dict[str, float]:
    is_train = optimizer is not None
    model.train(is_train)

    total_loss = 0.0
    total_dice = 0.0
    total_iou = 0.0
    total_samples = 0

    for images, masks in loader:
        images = images.to(device)
        masks = masks.to(device)
        batch_size = images.size(0)

        if is_train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(is_train):
            logits = model(images)
            loss = criterion(logits, masks)

            if is_train:
                loss.backward()
                optimizer.step()

        with torch.no_grad():
            d = dice_score(logits, masks)
            i = iou_score(logits, masks)

        total_loss += float(loss.item()) * batch_size
        total_dice += d * batch_size
        total_iou += i * batch_size
        total_samples += batch_size

    if total_samples == 0:
        return {"loss": 0.0, "dice": 0.0, "iou": 0.0}

    return {
        "loss": total_loss / total_samples,
        "dice": total_dice / total_samples,
        "iou": total_iou / total_samples,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Train binary plant segmentation from COCO polygons")
    p.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS_PATH)
    p.add_argument("--images_dir", type=Path, default=DEFAULT_IMAGES_DIR)
    p.add_argument("--output_dir", type=Path, default=DEFAULT_TRAIN_OUTPUT_DIR)
    p.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    p.add_argument("--batch_size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--lr", type=float, default=DEFAULT_LEARNING_RATE)
    p.add_argument("--weight_decay", type=float, default=1e-4)
    p.add_argument("--image_size", type=int, default=DEFAULT_IMAGE_SIZE)
    p.add_argument("--val_ratio", type=float, default=DEFAULT_VAL_RATIO)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--num_workers", type=int, default=0)
    p.add_argument("--max_images", type=int, default=0, help="0 means use all available images")
    p.add_argument("--architecture", default="unet", choices=["unet", "fpn", "deeplabv3plus"])
    p.add_argument("--encoder", default="resnet34")
    p.add_argument(
        "--encoder_weights",
        default="imagenet",
        help="imagenet or none",
    )
    p.add_argument("--device", default="auto", help="auto | cuda | cpu")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    seed_everything(args.seed)

    annotations_path = Path(args.annotations)
    images_dir = Path(args.images_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not annotations_path.exists():
        raise SystemExit(f"Annotations file not found: {annotations_path}")

    if not images_dir.exists():
        raise SystemExit(f"Images directory not found: {images_dir}")

    index = load_coco_index(annotations_path)
    all_image_ids = sorted(index.images.keys())

    if not all_image_ids:
        raise SystemExit("No images in COCO annotations.")

    missing = find_missing_images(images_dir, index)
    if missing:
        preview = ", ".join(missing[:5])
        print(f"[WARN] Missing {len(missing)} files from annotations in {images_dir}.")
        print(f"[WARN] Example missing files: {preview}")

    valid_image_ids = [
        image_id
        for image_id in all_image_ids
        if (images_dir / index.images[image_id].file_name).exists()
    ]

    if args.max_images > 0:
        valid_image_ids = valid_image_ids[: args.max_images]

    if len(valid_image_ids) < 2:
        raise SystemExit(
            "Need at least 2 valid images for train/val split. "
            "Check --images_dir and COCO file_name values."
        )

    train_ids, val_ids = split_image_ids(
        valid_image_ids,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )

    if not train_ids or not val_ids:
        raise SystemExit(
            f"Invalid split result. train={len(train_ids)}, val={len(val_ids)}. "
            "Adjust --val_ratio or dataset size."
        )

    image_size: Tuple[int, int] = (args.image_size, args.image_size)
    train_ds = CocoPolygonSegmentationDataset(
        index=index,
        image_ids=train_ids,
        images_dir=images_dir,
        image_size=image_size,
        augment=True,
    )
    val_ds = CocoPolygonSegmentationDataset(
        index=index,
        image_ids=val_ids,
        images_dir=images_dir,
        image_size=image_size,
        augment=False,
    )

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

    device = resolve_device(args.device)
    encoder_weights = None if str(args.encoder_weights).lower() == "none" else args.encoder_weights

    model = build_segmentation_model(
        architecture=args.architecture,
        encoder_name=args.encoder,
        encoder_weights=encoder_weights,
        in_channels=3,
        classes=1,
    ).to(device)

    criterion = BCEDiceLoss()
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=3,
        verbose=True,
    )

    best_val_dice = -1.0
    history = []

    print("Starting training")
    print(f"Device: {device}")
    print(f"Train images: {len(train_ids)} | Val images: {len(val_ids)}")
    print(f"Image size: {args.image_size}x{args.image_size}")
    print(f"Model: {args.architecture} / {args.encoder}")

    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(
            model=model,
            loader=train_loader,
            criterion=criterion,
            device=device,
            optimizer=optimizer,
        )
        val_metrics = run_epoch(
            model=model,
            loader=val_loader,
            criterion=criterion,
            device=device,
            optimizer=None,
        )

        scheduler.step(val_metrics["loss"])
        current_lr = float(optimizer.param_groups[0]["lr"])

        row = {
            "epoch": epoch,
            "lr": current_lr,
            "train_loss": train_metrics["loss"],
            "train_dice": train_metrics["dice"],
            "train_iou": train_metrics["iou"],
            "val_loss": val_metrics["loss"],
            "val_dice": val_metrics["dice"],
            "val_iou": val_metrics["iou"],
        }
        history.append(row)

        print(
            f"Epoch {epoch:03d}/{args.epochs} | "
            f"train_loss={row['train_loss']:.4f} val_loss={row['val_loss']:.4f} | "
            f"train_dice={row['train_dice']:.4f} val_dice={row['val_dice']:.4f} | "
            f"val_iou={row['val_iou']:.4f} lr={row['lr']:.2e}"
        )

        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": row,
            "args": vars(args),
        }
        torch.save(checkpoint, output_dir / "last.pt")

        if val_metrics["dice"] > best_val_dice:
            best_val_dice = val_metrics["dice"]
            torch.save(checkpoint, output_dir / "best.pt")
            print(f"Saved best checkpoint: val_dice={best_val_dice:.4f}")

    summary = {
        "best_val_dice": best_val_dice,
        "epochs": args.epochs,
        "train_images": len(train_ids),
        "val_images": len(val_ids),
        "history": history,
    }

    with (output_dir / "training_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Training finished. Best val_dice={best_val_dice:.4f}")
    print(f"Artifacts saved to: {output_dir}")


if __name__ == "__main__":
    main()
