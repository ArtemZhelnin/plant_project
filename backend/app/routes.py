import io
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image

from app.schemas import AnalysisResponse, Metrics

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from inference.model_loader import LoadedSegmentationModel, load_segmentation_model
from inference.predict import predict_plant
from train.config import load_calibration_config

router = APIRouter()


@lru_cache(maxsize=1)
def get_model_bundle() -> LoadedSegmentationModel:
    model_path = Path(os.getenv("PLANT_MODEL_PATH", PROJECT_ROOT / "weights/segmentation/best.pt"))
    model_device = os.getenv("PLANT_MODEL_DEVICE", "auto")
    model_threshold = float(os.getenv("PLANT_MODEL_THRESHOLD", "0.5"))

    return load_segmentation_model(
        weights_path=model_path,
        device=model_device,
        threshold=model_threshold,
    )


def _get_mm_per_pixel() -> Optional[float]:
    calibration_path = PROJECT_ROOT / "calibration" / "results.json"
    try:
        cfg = load_calibration_config(calibration_path)
        return float(cfg["mm_per_pixel"])
    except Exception:
        return None


@router.post("/predict", response_model=AnalysisResponse)
async def analyze_plant(image: UploadFile = File(...)):
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
        bundle = get_model_bundle()
        mm_per_pixel = _get_mm_per_pixel()
        pred = predict_plant(
            image_rgb=image_rgb,
            bundle=bundle,
            mm_per_pixel=mm_per_pixel,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Model file not found: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    metrics = Metrics(
        root_length_mm=float(pred["metrics"]["root_length_mm"]),
        stem_length_mm=float(pred["metrics"]["stem_length_mm"]),
        leaf_area_mm2=float(pred["metrics"]["leaf_area_mm2"]),
        root_area_mm2=float(pred["metrics"]["root_area_mm2"]),
    )

    return AnalysisResponse(
        metrics=metrics,
        overlay=str(pred["overlay"]),
        confidence=float(pred["confidence"]),
    )
