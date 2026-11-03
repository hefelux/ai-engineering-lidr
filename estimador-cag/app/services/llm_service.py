import logging

from anthropic import Anthropic

from fastapi import HTTPException

# Configuracion del .env
from app.config import settings

# Arma el system y el user prompt desde las plantillas de app/prompts
from app.prompts.loader import render_estimation_prompt

logger = logging.getLogger(__name__)

# Tokens de salida Max
MAX_TOKENS = 2000

# Precio por millon de tokens (de entrada, de salida)
PRICES = {
    "claude-haiku-4-5": (1.00, 5.00),
}


# Costo total de la llamada en dolares
def calculate_cost(input_tokens, output_tokens):

    # Si el modelo no esta en la lista de precios, devuelve 0
    if settings.llm_model not in PRICES:
        return 0.0

    input_price, output_price = PRICES[settings.llm_model]
    cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
    return round(cost, 6)


# Funcion principal: recibe lo que mando el formulario y devuelve la estimacion
def generate_estimation(request, version="v1"):
    system_prompt, user_prompt = render_estimation_prompt(request, version)
    logger.debug(f"Llamando a {settings.llm_provider} con el modelo {settings.llm_model}")

    # Por ahora solo esta implementado Anthropic
    if settings.llm_provider != "anthropic":
        raise HTTPException(status_code=500, detail="Solo esta implementado el proveedor anthropic (revisar LLM_PROVIDER en el .env)")

    try:
        # Llamada a Anthropic (system y user van separados)
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text

    # Si falla el proveedor (key, red, sin credito) se responde 502
    except Exception as e:
        logger.error(f"Error llamando al LLM: {e}")
        raise HTTPException(status_code=502, detail=f"Error llamando al LLM: {e}")

    # Tokens usados en la llamada
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    logger.debug(f"Tokens: {input_tokens} entrada, {output_tokens} salida")

    # Lo que se devuelve al router
    return {
        "text": text,
        "prompt_version": version,
        "model": response.model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": calculate_cost(input_tokens, output_tokens),
    }
