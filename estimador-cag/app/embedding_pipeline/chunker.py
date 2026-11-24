import tiktoken

from app.embedding_pipeline.schemas import Budget, Chunk

EMBEDDING_MODEL = "text-embedding-3-small"


# Corta los presupuestos siguiendo su estructura: un componente = un fragmento
# Sin overlap y sin cortar descripciones largas
class JSONStructuralChunker:

    def __init__(self):
        # el mismo tokenizador que usa el modelo de embeddings
        self.encoding = tiktoken.encoding_for_model(EMBEDDING_MODEL)

    def chunk(self, budgets: list[Budget]) -> list[Chunk]:
        chunks = []
        for budget in budgets:
            for component in budget.components:
                text = self._build_text(budget, component)
                metadata = {
                    "budget_id": budget.budget_id,
                    "component_id": component.component_id,
                    "client_sector": budget.client_metadata.sector,
                    "main_technology": budget.main_technology,
                    "year": budget.year,
                    "complexity": component.complexity,
                    "estimated_hours": component.estimated_hours,
                }
                chunks.append(
                    Chunk(
                        chunk_id=f"{budget.budget_id}::{component.component_id}",
                        text=text,
                        metadata=metadata,
                        token_count=len(self.encoding.encode(text)),
                    )
                )
        return chunks

    # Las dos primeras lineas son del presupuesto padre, para que un componente
    # como "Authentication backend" no pierda de que proyecto y sector es
    def _build_text(self, budget, component):
        lines = [
            f"[Project: {budget.project_summary}]",
            f"[Client sector: {budget.client_metadata.sector} | Year: {budget.year} | Main tech: {budget.main_technology}]",
            "",
            f"Component: {component.name}",
            f"Description: {component.description}",
            f"Tech stack: {', '.join(component.tech_stack)}",
            f"Complexity: {component.complexity}",
            f"Estimated hours: {component.estimated_hours}",
        ]
        return "\n".join(lines)
