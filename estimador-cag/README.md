# Estimador CAG

API hecha con FastAPI.
Recibe la transcripción de una reunión con un cliente y devuelve una estimación del proyecto (tareas, horas, equipo y duración) generada con Claude.

## Requisitos

- Python 3.11+
- uv
- API key de Anthropic

## Cómo correrlo

```
uv sync
cp .env.example .env
```

Poner la API key en el .env (ANTHROPIC_API_KEY), junto con LLM_PROVIDER=anthropic y LLM_MODEL=claude-haiku-4-5, y después:

```
uv run uvicorn app.main:app --reload
```

La documentación queda en http://localhost:8000/docs

## Probar

```
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{"transcription": "El cliente necesita una landing page con formulario de contacto..."}'
```

La transcripción que usé para probar está en data/transcripcion-reunion.txt

Con esa transcripción y claude-haiku-4-5 la llamada usó ~1070 tokens de entrada y ~480 de salida (unos $0.003). La mayoría de la entrada son los ejemplos del contexto.

## Tests

```
uv run pytest
```

Revisan la estructura de carpetas, /health, /docs, que el prompt incluya los ejemplos y el endpoint de estimación (con una respuesta falsa para no gastar créditos). También corren en GitHub Actions en cada push.

## Estructura

- app/main.py: crea la app y el endpoint /health
- app/config.py: lee las variables del .env
- app/routers/estimations.py: endpoint POST /api/v1/estimate
- app/services/llm_service.py: arma el prompt con los ejemplos y llama a Claude
- app/context/examples.py: estimaciones de ejemplo
