import io
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from app.schemas import AnalysisResponse, Metrics

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from inference.model_loader import LoadedSegmentationModel, load_segmentation_model
from inference.predict import predict_plant
from inference.yolo_predict import LoadedYoloModel, load_yolo_segmentation_model, predict_plant_yolo
from train.config import load_calibration_config

router = APIRouter()


@lru_cache(maxsize=1)
def get_model_bundle() -> LoadedSegmentationModel:
    preferred_default = PROJECT_ROOT / "weights/segmentation_multiclass_max_gpu/best.pt"
    fallback_multiclass = PROJECT_ROOT / "weights/segmentation_multiclass_max/best.pt"
    fallback_binary = PROJECT_ROOT / "weights/segmentation/best.pt"

    env_path = os.getenv("PLANT_MODEL_PATH")
    if env_path:
        model_path = Path(env_path)
    elif preferred_default.exists():
        model_path = preferred_default
    elif fallback_multiclass.exists():
        model_path = fallback_multiclass
    else:
        model_path = fallback_binary

    model_device = os.getenv("PLANT_MODEL_DEVICE", "auto")
    model_threshold = float(os.getenv("PLANT_MODEL_THRESHOLD", "0.5"))

    return load_segmentation_model(
        weights_path=model_path,
        device=model_device,
        threshold=model_threshold,
    )


@lru_cache(maxsize=1)
def get_yolo_bundle() -> LoadedYoloModel:
    env_path = os.getenv("PLANT_YOLO_MODEL_PATH")
    model_path = Path(env_path) if env_path else (PROJECT_ROOT / "weightsYOLO" / "best.pt")
    model_device = os.getenv("PLANT_MODEL_DEVICE", "auto")
    return load_yolo_segmentation_model(weights_path=model_path, device=model_device)


def _get_mm_per_pixel() -> Optional[float]:
    calibration_path = PROJECT_ROOT / "calibration" / "results.json"
    try:
        cfg = load_calibration_config(calibration_path)
        return float(cfg["mm_per_pixel"])
    except Exception:
        return None


@router.post("/predict", response_model=AnalysisResponse)
async def analyze_plant(
    image: UploadFile = File(...),
    model_type: Literal["unet", "yolo"] = Form("unet"),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await image.read()
    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}") from exc

    image_rgb = np.asarray(img, dtype=np.uint8)

    try:
        selected_model = str(model_type).lower()
        mm_per_pixel = _get_mm_per_pixel()
        if selected_model == "yolo":
            bundle_yolo = get_yolo_bundle()
            pred = predict_plant_yolo(
                image_rgb=image_rgb,
                bundle=bundle_yolo,
                mm_per_pixel=mm_per_pixel,
            )
            loaded_num_classes = 4
            class_names = pred.get("class_names", ["background", "leaf", "root", "stem"])
            loaded_model_type = "yolo"
        else:
            bundle = get_model_bundle()
            pred = predict_plant(
                image_rgb=image_rgb,
                bundle=bundle,
                mm_per_pixel=mm_per_pixel,
            )
            loaded_num_classes = int(bundle.num_classes)
            class_names = [str(x) for x in bundle.class_names]
            loaded_model_type = "unet"
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Model file not found: {exc}") from exc
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    metrics = Metrics(
        root_length_mm=float(pred["metrics"]["root_length_mm"]),
        stem_length_mm=float(pred["metrics"]["stem_length_mm"]),
        leaf_area_mm2=float(pred["metrics"]["leaf_area_mm2"]),
        root_area_mm2=float(pred["metrics"]["root_area_mm2"]),
        stem_area_mm2=float(pred["metrics"].get("stem_area_mm2", 0.0)),
    )

    return AnalysisResponse(
        metrics=metrics,
        overlay=str(pred["overlay"]),
        confidence=float(pred["confidence"]),
        loaded_num_classes=loaded_num_classes,
        class_names=[str(x) for x in class_names],
        loaded_model_type=loaded_model_type,
    )
