from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ollama_bridge import generate_completion

router = APIRouter(prefix="/vision", tags=["vision"])

class VisionRequest(BaseModel):
    image_base64: str
    prompt: str = "Describe this medical image."

@router.post("/analyze")
async def analyze_image(request: VisionRequest):
    # Uses LLaVA-Phi3 - Vision Model
    
    # Check if base64 header exists and remove it if so
    img_data = request.image_base64
    if "," in img_data:
        img_data = img_data.split(",")[1]
        
    response = await generate_completion(
        model="llava-phi3",
        prompt=request.prompt,
        system=None,
        images=[img_data],
        options={
            "temperature": 0.2
        }
    )
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
        
    return {
        "analysis": response.get("response", "").strip(),
        "model_used": "llava-phi3"
    }
