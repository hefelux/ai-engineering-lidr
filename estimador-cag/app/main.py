import logging

from fastapi import FastAPI

from app.config import settings
from app.routers import estimations

# Nivel de logs segun el LOG_LEVEL del .env
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Estimador CAG",
    description="Recibe la transcripción de una reunión y devuelve una estimación de software generada con un LLM.",
)

# Agrega el router de estimaciones con el prefijo /api/v1
app.include_router(estimations.router, prefix="/api/v1")


# Endpoint para revisar que el servicio esta arriba
@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}
