import hashlib
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined

logger = structlog.get_logger()

# Carpeta con las versiones del prompt de estimacion (v1, v2...)
PROMPTS_DIR = Path(__file__).parent / "estimation"


# Arma el system y el user prompt a partir de lo que llego del formulario
def render_estimation_prompt(request, version="v1"):
    env = Environment(
        # Cada version es una carpeta con sus plantillas
        loader=FileSystemLoader(PROMPTS_DIR / version),
        # Si falta una variable da error (en vez de dejarla vacia)
        undefined=StrictUndefined,
        # Para que los {% if %} no dejen lineas en blanco
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Los enums se pasan como texto ("phases_table") para compararlos en las plantillas
    variables = {
        "description": request.description,
        "project_type": request.project_type.value,
        "detail_level": request.detail_level.value,
        "output_format": request.output_format.value,
        "reference_projects": request.reference_projects,
    }

    system_prompt = env.get_template("system.j2").render(variables)
    user_prompt = env.get_template("user.j2").render(variables)

    # Hash del prompt final, para saber con que prompt salio cada estimacion
    prompt_hash = hashlib.sha256((system_prompt + user_prompt).encode()).hexdigest()[:12]
    logger.info("prompt_rendered", version=version, prompt_hash=prompt_hash)

    return system_prompt, user_prompt
