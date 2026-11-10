from enum import Enum

from pydantic import BaseModel, Field

from app.sessions import ProjectMetadata


# Opciones del formulario (si llega un valor que no esta en la lista, FastAPI responde 422)
class ProjectType(str, Enum):
    mobile_app = "mobile_app"
    web_saas = "web_saas"
    internal_tool = "internal_tool"
    data_pipeline = "data_pipeline"


class DetailLevel(str, Enum):
    summary = "summary"
    medium = "medium"
    detailed = "detailed"


class OutputFormat(str, Enum):
    phases_table = "phases_table"
    line_items = "line_items"
    narrative = "narrative"


# Versiones del prompt que existen (carpetas dentro de app/prompts/estimation)
class PromptVersion(str, Enum):
    v1 = "v1"
    v2 = "v2"


# Un proyecto parecido que ya se hizo, para que el modelo tenga una referencia de horas
class ReferenceProject(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    hours: int = Field(gt=0)


# Datos que manda el formulario
class EstimationRequest(BaseModel):
    # Descripcion del proyecto (entre 20 y 2000 caracteres)
    description: str = Field(min_length=20, max_length=2000)

    # Opciones de los selectores
    project_type: ProjectType
    detail_level: DetailLevel
    output_format: OutputFormat

    # Opcional, si no se manda queda vacia
    reference_projects: list[ReferenceProject] = Field(default=[], max_length=5)


# Datos que devuelve la API
class EstimationResponse(BaseModel):
    # Estimacion en texto libre (markdown)
    text: str

    # Version del prompt que se uso (carpeta dentro de app/prompts/estimation)
    prompt_version: str

    # Modelo que respondio
    model: str

    # Tokens de entrada y de salida
    input_tokens: int
    output_tokens: int

    # Costo total de la llamada en dolares (aproximado)
    cost_usd: float


# Respuesta de POST /sessions
class SessionCreated(BaseModel):
    session_id: str


# Respuesta de un turno de la conversacion: la misma estimacion de antes mas el estado de la sesion
class SessionEstimationResponse(EstimationResponse):
    session_id: str

    # Lo que sabemos del proyecto despues de este turno
    project_metadata: ProjectMetadata

    # Turnos que hay en el historial (como maximo MAX_TURNS)
    history_turns: int

    # Costo de la segunda llamada, la que actualiza el project_metadata
    extractor_cost_usd: float
