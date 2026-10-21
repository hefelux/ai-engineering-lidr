# APIRouter 
from fastapi import APIRouter

# Definición de los datos que entran y salen
from pydantic import BaseModel

# Funcion que arma el prompt y llama al LLM
from app.services.llm_service import generate_estimation

router = APIRouter()

# Datos que tiene que mandar el cliente (Transcripcion de la reunion)
class EstimateRequest(BaseModel):
    transcription: str


# Datos que devuelve la API
class EstimateResponse(BaseModel):
    # Estimacion que genera el modelo (Texto en markdown)
    estimation: str

    # Modelo que respondio
    model: str

    # anthropic
    provider: str

    # Tokens que de entrada (prompt + ejemplos + transcripcion)
    input_tokens: int

    # Tokens que de salida (generados por el modelo)
    output_tokens: int

    # Costo total de la llamada en dolares (aproximado)
    cost_usd: float


# Endpoint POST /api/v1/estimate, response_model hace que la respuesta siga EstimateResponse
@router.post("/estimate", response_model=EstimateResponse)
def estimate(request: EstimateRequest):
    # Llamada a la funcion que genera la estimacion
    return generate_estimation(request.transcription)
