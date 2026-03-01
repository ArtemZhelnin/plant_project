import argparse
import glob
import json
import os
from typing import Dict, List, Tuple

import cv2

from calibration.detect_corners import detect_chessboard_corners
from calibration.compute_scale import compute_mm_per_pixel, to_dict as scale_to_dict
from calibration.stats import compute_stats, filter_outliers, to_dict as stats_to_dict


def _parse_pattern(s: str) -> Tuple[int, int]:
    parts = s.lower().replace("x", ",").split(",")
    if len(parts) != 2:
        raise ValueError("pattern must be inner corners colsxrows, e.g. 4x7")
    a = int(parts[0].strip())
    b = int(parts[1].strip())
    return (a, b)


def _quality_label(relative_std_percent: float) -> str:
    if relative_std_percent < 1.0:
        return "camera_ideal"
    if relative_std_percent < 3.0:
        return "normal"
    if relative_std_percent < 5.0:
        return "acceptable"
    return "problem"


def main() -> None:
    p = argparse.ArgumentParser(description="Estimate mm_per_pixel from chessboard images")
    p.add_argument("--input_glob", default="data/calib/calib_*.jpg")
    p.add_argument(
        "--pattern",
        default="4x7",
        help="inner corners pattern colsxrows, e.g. 4x7 for a 5x8 squares board",
    )
    p.add_argument("--square_mm", type=float, default=10.0)
    p.add_argument("--out", default="calibration/results.json")
    p.add_argument("--outlier_z", type=float, default=2.0)
    p.add_argument(
        "--max_images",
        type=int,
        default=0,
        help="limit number of images for quick checks (0 = use all)",
    )

    args = p.parse_args()

    pattern_size = _parse_pattern(args.pattern)

    paths = sorted(glob.glob(args.input_glob))
    if not paths:
        raise SystemExit(f"No images found by glob: {args.input_glob}")
    if args.max_images > 0:
        paths = paths[: args.max_images]

    per_image: List[Dict[str, object]] = []
    mm_values: List[float] = []
    used_paths: List[str] = []

    for idx, path in enumerate(paths, start=1):
        print(f"[{idx}/{len(paths)}] {path}")
        img = cv2.imread(path)
        det = detect_chessboard_corners(img, pattern_size)
        if det is None:
            per_image.append({"path": path, "status": "not_found"})
            continue

        scale = compute_mm_per_pixel(det, square_size_mm=args.square_mm)
        per_image.append({"path": path, "status": "ok", **scale_to_dict(scale)})
        mm_values.append(scale.mm_per_pixel)
        used_paths.append(path)

    if not mm_values:
        raise SystemExit("No valid detections. Check pattern size (inner corners) and image quality.")

    stats_all = compute_stats(mm_values)
    filt = filter_outliers(mm_values, z=args.outlier_z)

    kept_idx = filt["kept_idx"]
    dropped_idx = filt["dropped_idx"]
    kept_values = filt["values_kept"]

    stats_kept = compute_stats(kept_values) if kept_values else stats_all

    dropped_paths = [used_paths[i] for i in dropped_idx]
    kept_paths = [used_paths[i] for i in kept_idx]

    result = {
        "mm_per_pixel": stats_kept.mean,
        "std": stats_kept.std,
        "relative_std": stats_kept.relative_std_percent,
        "images_used": len(kept_values),
        "quality": _quality_label(stats_kept.relative_std_percent),
        "input_glob": args.input_glob,
        "pattern_inner_corners": {"cols": pattern_size[0], "rows": pattern_size[1]},
        "square_size_mm": args.square_mm,
        "images_total": len(paths),
        "images_detected": len(used_paths),
        "images_rejected_outliers": len(dropped_paths),
        "outlier_rule": {"type": "abs(x-mean) > z*std", "z": args.outlier_z},
        "notes": [
            "Scale must be estimated on original image resolution (no resize before calibration).",
            "Use the same camera setup for calibration images and plant measurements.",
        ],
        "details": {
            "stats_before_outlier_filter": stats_to_dict(stats_all),
            "stats_after_outlier_filter": stats_to_dict(stats_kept),
            "kept_images": kept_paths,
            "dropped_outliers": dropped_paths,
            "per_image": per_image,
        },
    }

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("Done.")
    print(f"Images total: {len(paths)}")
    print(f"Detected chessboards: {len(used_paths)}")
    print(f"Used after outlier filter: {len(kept_values)}")
    print(f"Final mm_per_pixel: {stats_kept.mean:.8f}")
    print(f"Std: {stats_kept.std:.8f} ({stats_kept.relative_std_percent:.2f}%)")
    print(f"Quality: {_quality_label(stats_kept.relative_std_percent)}")
    if dropped_paths:
        print("Dropped outliers:")
        for dp in dropped_paths:
            print(f"  - {dp}")


if __name__ == "__main__":
    main()
