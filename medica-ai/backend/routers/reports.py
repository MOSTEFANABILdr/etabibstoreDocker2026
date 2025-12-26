from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ollama_bridge import generate_completion

router = APIRouter(prefix="/reports", tags=["reports"])

class ReportRequest(BaseModel):
    text: str
    context: str = "Summarize this medical report in a concise professional manner."

@router.post("/summarize")
async def summarize_report(request: ReportRequest):
    # Uses MedGemma 4B - CPU Optimized
    full_prompt = f"Context: {request.context}\nInput: {request.text}\nSummary:"
    
    response = await generate_completion(
        model="alibayram/medgemma:4b",
        prompt=full_prompt,
        system=None, 
        options={
            "temperature": 0.2,
            "num_docs": 0 
        }
    )
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
        
    return {
        "summary": response.get("response", "").strip(),
        "model_used": "medgemma:4b"
    }
