import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np

from inference.model_loader import LoadedSegmentationModel, load_segmentation_model
from inference.postprocessing import (
    estimate_metrics_from_mask,
    image_to_data_uri,
    make_overlay_image,
)
from inference.preprocessing import preprocess_image
from train.config import get_mm_per_pixel


def _infer_prob_map(
    image_rgb: np.ndarray,
    bundle: LoadedSegmentationModel,
) -> np.ndarray:
    x_t, (orig_h, orig_w) = preprocess_image(image_rgb, bundle.image_size)
    x_t = x_t.to(bundle.device)

    import torch

    with torch.no_grad():
        logits = bundle.model(x_t)
        probs = torch.sigmoid(logits)[0, 0].detach().cpu().numpy().astype(np.float32)

    prob_map = cv2.resize(probs, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    return prob_map


def predict_plant(
    image_rgb: np.ndarray,
    bundle: LoadedSegmentationModel,
    mm_per_pixel: Optional[float] = None,
    threshold: Optional[float] = None,
) -> Dict[str, object]:
    prob_map = _infer_prob_map(image_rgb, bundle=bundle)
    th = bundle.threshold if threshold is None else float(threshold)

    mask = (prob_map >= th).astype(np.uint8)
    overlay = make_overlay_image(image_rgb=image_rgb, mask_binary=mask)
    overlay_data_uri = image_to_data_uri(overlay)

    metrics = estimate_metrics_from_mask(mask_binary=mask, mm_per_pixel=mm_per_pixel)
    confidence = float(np.mean(np.maximum(prob_map, 1.0 - prob_map)))

    return {
        "metrics": metrics,
        "overlay": overlay_data_uri,
        "confidence": confidence,
        "mask": mask,
        "probability_map": prob_map,
    }


def _save_mask_png(mask: np.ndarray, out_path: Path) -> None:
    out = (mask > 0).astype(np.uint8) * 255
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
    p.add_argument("--weights", type=Path, default=Path("weights/segmentation/best.pt"))
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
