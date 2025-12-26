from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os

router = APIRouter(prefix="/admin", tags=["Admin"])

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

class PullRequest(BaseModel):
    model_name: str

@router.post("/pull_model")
async def pull_model(request: PullRequest):
    url = f"{OLLAMA_HOST}/api/pull"
    payload = {"name": request.model_name, "stream": False}
    
    async with httpx.AsyncClient(timeout=600.0) as client: # Long timeout for download
        try:
            # We trigger it. Note: fast pull without stream might timeout HTTP but continue on server
            # Better to just fire and return "started" if possible, but Ollama waits.
            # For simplicity, we wait.
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return {"status": "success", "detail": response.json()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
