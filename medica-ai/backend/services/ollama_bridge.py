import httpx
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

async def generate_completion(model: str, prompt: str, system: str = None, images: list = None, options: dict = None):
    url = f"{OLLAMA_HOST}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    if system:
        payload["system"] = system

    if images:
        payload["images"] = images
        
    if options:
        payload["options"] = options
        
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return {"error": str(e)}
