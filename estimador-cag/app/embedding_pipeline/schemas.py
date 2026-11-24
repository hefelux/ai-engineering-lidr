from typing import Literal

from pydantic import BaseModel, Field

# Sectores y complejidades que aparecen en data/budgets_sample.json
# Si llega otro valor, la API responde 422
Sector = Literal["finance", "ecommerce", "healthcare", "industrial"]
Complexity = Literal["low", "medium", "high"]


class ClientMetadata(BaseModel):
    name: str
    sector: Sector
    country: str = Field(min_length=2, max_length=2)


# Un componente del presupuesto, con todos los campos del JSON
class BudgetComponent(BaseModel):
    component_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tech_stack: list[str] = []
    estimated_hours: int = Field(ge=0)
    complexity: Complexity
    dependencies: list[str] = []


# Un presupuesto completo
class Budget(BaseModel):
    budget_id: str = Field(min_length=1)
    client_metadata: ClientMetadata
    project_summary: str = Field(min_length=1)
    main_technology: str
    year: int = Field(ge=2000, le=2100)
    total_estimated_hours: int = Field(ge=0)
    components: list[BudgetComponent] = Field(min_length=1)


# Un fragmento listo para mandar a la API de embeddings
# Solo "text" se vectoriza, la metadata viaja al lado para filtrar despues
class Chunk(BaseModel):
    chunk_id: str
    text: str
    metadata: dict
    token_count: int


# El mismo fragmento con su vector
class EmbeddedChunk(Chunk):
    embedding: list[float]


class IngestRequest(BaseModel):
    budgets: list[Budget] = Field(min_length=1)


class IngestStats(BaseModel):
    total_budgets: int
    total_chunks: int
    total_tokens: int
    estimated_cost_usd: float


class IngestResponse(BaseModel):
    chunks: list[EmbeddedChunk]
    stats: IngestStats
