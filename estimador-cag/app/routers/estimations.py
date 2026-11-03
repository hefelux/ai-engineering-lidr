# APIRouter 
from fastapi import APIRouter

# Datos que entran (formulario) y salen (estimacion)
from app.schemas import EstimationRequest, EstimationResponse, PromptVersion

# Funcion que arma el prompt y llama al LLM
from app.services.llm_service import generate_estimation

router = APIRouter()


# Endpoint POST /api/v1/estimate, la version del prompt va en la URL (?prompt_version=v2)
@router.post("/estimate", response_model=EstimationResponse)
def estimate(request: EstimationRequest, prompt_version: PromptVersion = PromptVersion.v1):
    return generate_estimation(request, prompt_version.value)
