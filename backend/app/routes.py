import asyncio
from fastapi import APIRouter, File, UploadFile, HTTPException
import base64
import io
import random
from PIL import Image

from app.schemas import AnalysisResponse, Metrics

router = APIRouter()

@router.post("/predict", response_model=AnalysisResponse)
async def analyze_plant(image: UploadFile = File(...)):
    """
    Analyze plant image and return segmentation metrics
    """
    try:
        # Validate file type
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        # Read and validate image
        contents = await image.read()
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()  # Verify image integrity
            img = Image.open(io.BytesIO(contents))  # Reopen after verify
        except Exception:
            raise HTTPException(status_code=400, detail="Некорректный файл изображения")
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Mock analysis - replace with actual model inference
        await simulate_processing()
        
        # Generate mock metrics
        metrics = Metrics(
            root_length_mm=round(random.uniform(30.0, 60.0), 1),
            stem_length_mm=round(random.uniform(20.0, 40.0), 1),
            leaf_area_mm2=round(random.uniform(200.0, 500.0), 1),
            root_area_mm2=round(random.uniform(80.0, 200.0), 1)
        )
        
        # Create mock overlay (just return original for now)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        confidence = round(random.uniform(0.85, 0.98), 2)
        
        return AnalysisResponse(
            metrics=metrics,
            overlay=img_str,
            confidence=confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

async def simulate_processing():
    """Simulate model processing time"""
    await asyncio.sleep(2.0)  # 2 second processing time
