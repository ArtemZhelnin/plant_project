from pydantic import BaseModel
from typing import List, Optional

class Metrics(BaseModel):
    root_length_mm: float
    stem_length_mm: float
    leaf_area_mm2: float
    root_area_mm2: float
    stem_area_mm2: float = 0.0

class AnalysisResponse(BaseModel):
    metrics: Metrics
    overlay: str  # base64 encoded image
    confidence: float
    loaded_num_classes: int = 1
    class_names: List[str] = []
    loaded_model_type: str = "unet"

class HealthResponse(BaseModel):
    status: str
