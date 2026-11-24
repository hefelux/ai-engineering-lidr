import structlog
from fastapi import APIRouter, HTTPException

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import OpenAIEmbedder, estimate_cost
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse

logger = structlog.get_logger()

router = APIRouter()


# Recibe presupuestos y devuelve sus fragmentos con vector y las estadisticas
# Si el body no cumple los schemas, FastAPI responde 422 solo
@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest):
    chunks = JSONStructuralChunker().chunk(request.budgets)

    try:
        embedded = OpenAIEmbedder().embed_many(chunks)
    except Exception as e:
        # el detalle queda en los logs, al cliente le llega un mensaje generico
        logger.error("embedding_failed", error=repr(e))
        raise HTTPException(status_code=500, detail="No se pudieron generar los embeddings.")

    total_tokens = sum(chunk.token_count for chunk in embedded)
    stats = {
        "total_budgets": len(request.budgets),
        "total_chunks": len(embedded),
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimate_cost(total_tokens),
    }
    return {"chunks": embedded, "stats": stats}
