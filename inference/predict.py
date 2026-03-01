import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np

from inference.model_loader import LoadedSegmentationModel, load_segmentation_model
from inference.postprocessing import (
    estimate_metrics_from_mask,
    estimate_metrics_from_multiclass_mask,
    image_to_data_uri,
    make_overlay_image,
    make_multiclass_overlay_image,
)
from inference.preprocessing import preprocess_image
from train.config import get_mm_per_pixel


def _softmax_np(x: np.ndarray, axis: int) -> np.ndarray:
    m = np.max(x, axis=axis, keepdims=True)
    e = np.exp(x - m)
    d = np.sum(e, axis=axis, keepdims=True)
    return e / np.clip(d, 1e-8, None)


def _infer_logits(
    image_rgb: np.ndarray,
    bundle: LoadedSegmentationModel,
) -> np.ndarray:
    x_t, (orig_h, orig_w) = preprocess_image(image_rgb, bundle.image_size)
    x_t = x_t.to(bundle.device)

    import torch

    with torch.no_grad():
        logits = bundle.model(x_t)[0].detach().cpu().numpy().astype(np.float32)

    # logits: [C, h, w] -> [H, W, C] -> resize -> [C, H, W]
    logits_hwc = np.transpose(logits, (1, 2, 0))
    logits_resized = cv2.resize(logits_hwc, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    if logits_resized.ndim == 2:
        logits_resized = logits_resized[:, :, None]
    return np.transpose(logits_resized, (2, 0, 1)).astype(np.float32)


def _predict_binary(
    image_rgb: np.ndarray,
    logits: np.ndarray,
    bundle: LoadedSegmentationModel,
    mm_per_pixel: Optional[float],
    threshold: Optional[float],
) -> Dict[str, object]:
    prob_map = 1.0 / (1.0 + np.exp(-logits[0]))
    th = bundle.threshold if threshold is None else float(threshold)
    mask = (prob_map >= th).astype(np.uint8)
    overlay = make_overlay_image(image_rgb=image_rgb, mask_binary=mask)
    metrics = estimate_metrics_from_mask(mask_binary=mask, mm_per_pixel=mm_per_pixel)
    confidence = float(np.mean(np.maximum(prob_map, 1.0 - prob_map)))
    return {
        "metrics": metrics,
        "overlay": image_to_data_uri(overlay),
        "confidence": confidence,
        "mask": mask,
        "probability_map": prob_map,
    }


def _predict_multiclass(
    image_rgb: np.ndarray,
    logits: np.ndarray,
    bundle: LoadedSegmentationModel,
    mm_per_pixel: Optional[float],
) -> Dict[str, object]:
    probs = _softmax_np(logits, axis=0)
    mask = np.argmax(probs, axis=0).astype(np.uint8)
    overlay = make_multiclass_overlay_image(image_rgb=image_rgb, mask_classes=mask)
    metrics = estimate_metrics_from_multiclass_mask(mask_classes=mask, mm_per_pixel=mm_per_pixel)

    max_probs = np.max(probs, axis=0)
    fg = mask > 0
    if np.any(fg):
        confidence = float(np.mean(max_probs[fg]))
    else:
        confidence = float(np.mean(max_probs))

    return {
        "metrics": metrics,
        "overlay": image_to_data_uri(overlay),
        "confidence": confidence,
        "mask": mask,
        "probability_map": probs,
    }


def predict_plant(
    image_rgb: np.ndarray,
    bundle: LoadedSegmentationModel,
    mm_per_pixel: Optional[float] = None,
    threshold: Optional[float] = None,
) -> Dict[str, object]:
    logits = _infer_logits(image_rgb, bundle=bundle)
    if bundle.num_classes <= 1:
        return _predict_binary(
            image_rgb=image_rgb,
            logits=logits,
            bundle=bundle,
            mm_per_pixel=mm_per_pixel,
            threshold=threshold,
        )
    return _predict_multiclass(
        image_rgb=image_rgb,
        logits=logits,
        bundle=bundle,
        mm_per_pixel=mm_per_pixel,
    )


def _save_mask_png(mask: np.ndarray, out_path: Path) -> None:
    if mask.ndim != 2:
        raise ValueError("mask must be 2D")
    if int(mask.max()) <= 1:
        out = (mask > 0).astype(np.uint8) * 255
    else:
        out = mask.astype(np.uint8)
    cv2.imwrite(str(out_path), out)


def _save_overlay_png(overlay_data_uri: str, out_path: Path) -> None:
    # overlay_data_uri: data:image/png;base64,....
    b64 = overlay_data_uri.split(",", 1)[1]
    import base64

    raw = base64.b64decode(b64)
    out_path.write_bytes(raw)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Run plant segmentation inference on one image")
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--weights", type=Path, default=Path("weights/segmentation_multiclass_max_gpu/best.pt"))
    p.add_argument("--out_dir", type=Path, default=Path("data/processed"))
    p.add_argument("--device", default="auto", help="auto | cpu | cuda")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--use_calibration", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    image_path = Path(args.image)
    if not image_path.exists():
        raise SystemExit(f"Image file not found: {image_path}")

    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise SystemExit(f"Cannot read image: {image_path}")
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    bundle = load_segmentation_model(
        weights_path=args.weights,
        device=args.device,
        threshold=args.threshold,
    )

    mm_per_pixel = None
    if args.use_calibration:
        try:
            mm_per_pixel = get_mm_per_pixel()
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] calibration unavailable: {exc}")

    pred = predict_plant(
        image_rgb=image_rgb,
        bundle=bundle,
        mm_per_pixel=mm_per_pixel,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = image_path.stem

    mask_path = out_dir / f"{stem}_mask.png"
    overlay_path = out_dir / f"{stem}_overlay.png"
    result_path = out_dir / f"{stem}_result.json"

    _save_mask_png(pred["mask"], mask_path)
    _save_overlay_png(pred["overlay"], overlay_path)

    payload = {
        "image": str(image_path),
        "weights": str(args.weights),
        "confidence": float(pred["confidence"]),
        "metrics": pred["metrics"],
        "mask_path": str(mask_path),
        "overlay_path": str(overlay_path),
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Inference complete")
    print(f"Mask: {mask_path}")
    print(f"Overlay: {overlay_path}")
    print(f"JSON: {result_path}")
    print(f"Confidence: {payload['confidence']:.4f}")


if __name__ == "__main__":
    main()
