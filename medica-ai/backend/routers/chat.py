from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ollama_bridge import generate_completion
from typing import Optional

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    model: str = "cniongolo/biomistral"
    system_prompt: Optional[str] = None
    image_base64: Optional[str] = None

@router.post("/completions")
async def chat_completion(request: ChatRequest):
    # Generic endpoint for the Web UI
    
    prompt = request.message
    images = []
    
    if request.image_base64:
        # Handle Base64 image
        img_data = request.image_base64
        if "," in img_data:
            img_data = img_data.split(",")[1]
        images.append(img_data)

    response = await generate_completion(
        model=request.model,
        prompt=prompt,
        system=request.system_prompt,
        images=images,
        options={
            "temperature": 0.2 
        }
    )
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
        
    return {
        "response": response.get("response", "").strip(),
        "model": request.model
    }
