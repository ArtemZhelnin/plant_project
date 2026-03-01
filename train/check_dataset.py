import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser("Validate COCO polygons dataset paths")
    p.add_argument("--annotations", type=Path, default=Path("annotations/instances_default.json"))
    p.add_argument("--images_dir", type=Path, default=Path("data/rukola"))
    args = p.parse_args()

    if not args.annotations.exists():
        raise SystemExit(f"Annotations file not found: {args.annotations}")
    if not args.images_dir.exists():
        raise SystemExit(f"Images dir not found: {args.images_dir}")

    with args.annotations.open("r", encoding="utf-8") as f:
        data = json.load(f)

    images = data.get("images", [])
    annotations = data.get("annotations", [])
    categories = data.get("categories", [])

    missing = []
    for img in images:
        file_name = img.get("file_name")
        if not file_name:
            continue
        if not (args.images_dir / file_name).exists():
            missing.append(file_name)

    invalid_polygons = 0
    for ann in annotations:
        seg = ann.get("segmentation")
        if not isinstance(seg, list):
            continue
        for poly in seg:
            if not isinstance(poly, list) or len(poly) < 6 or len(poly) % 2 != 0:
                invalid_polygons += 1

    print(f"images: {len(images)}")
    print(f"annotations: {len(annotations)}")
    print(f"categories: {len(categories)}")
    print(f"missing_images: {len(missing)}")
    print(f"invalid_polygons: {invalid_polygons}")

    if missing:
        print("First missing files:")
        for file_name in missing[:10]:
            print(f"  - {file_name}")

        raise SystemExit(
            "Dataset is incomplete. Put image files into --images_dir "
            "or pass the correct folder via --images_dir."
        )

    print("Dataset paths look good.")


if __name__ == "__main__":
    main()
