from pydantic import BaseModel
from typing import Optional

class Metrics(BaseModel):
    root_length_mm: float
    stem_length_mm: float
    leaf_area_mm2: float
    root_area_mm2: float

class AnalysisResponse(BaseModel):
    metrics: Metrics
    overlay: str  # base64 encoded image
    confidence: float

class HealthResponse(BaseModel):
    status: str
