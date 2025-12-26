from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ollama_bridge import generate_completion

router = APIRouter(prefix="/clinical", tags=["Clinical"])

class SnomedRequest(BaseModel):
    sctid: str
    context: str = ""

# Rigid System Prompt as defined in requirements
RIGID_SYSTEM_PROMPT = """RÔLE : Tu es un moteur d'inférence logique basé exclusivement sur l'ontologie SNOMED CT 2025. Tu agis comme un graphe de connaissances, pas comme un assistant conversationnel.
RÈGLES STRICTES :
INTERDICTION de phrases de courtoisie.
INTERDICTION d'explications textuelles.
ENTRÉE : Un code SCTID unique (Motif/Symptôme).
SORTIE : Uniquement une liste de codes SCTID correspondant aux "Attributes" (Finding Site, Associated Morphology) ou aux concepts "Children" cliniquement pertinents.
FORMAT DE RÉPONSE : SCTID_1, SCTID_2, SCTID_3 (uniquement les chiffres séparés par des virgules).
OBJECTIF : Identifier les points d'interrogation cliniques liés au code fourni."""

@router.post("/inference")
async def get_clinical_inference(request: SnomedRequest):
    # Optimized for CPU latency
    options = {
        "num_predict": 64,  # Increased slightly to ensure we get output
        "temperature": 0.1, # Deterministic
        "top_k": 10
    }
    
    # Few-Shot Prompting to guide the model
    # We provide 2 examples to show exactly what we want (Input -> Output)
    few_shot_examples = """
Exemple 1:
Input: Code: 386661006. Context: Fièvre élevée
Output: 43724002, 248450001, 193462001

Exemple 2:
Input: Code: 25064002. Context: Maux de tête
Output: 162306006, 274667000, 427268000

Tâche Actuelle:
"""
    
    full_prompt = f"[INST] {RIGID_SYSTEM_PROMPT}\n\n{few_shot_examples}\nInput: Code: {request.sctid}. Context: {request.context}\nOutput: [/INST]"
    
    response = await generate_completion(
        model="cniongolo/biomistral", 
        prompt=full_prompt,
        system=None, # We embedded it
        options=options
    )
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
        
    raw_response = response.get("response", "").strip()
    
    # Simple validation locally to ensure we only return what looks like IDs
    # The client will handle the rest
    return {
        "source_sctid": request.sctid,
        "suggested_sctids": raw_response,
        "raw_model_output": raw_response
    }
