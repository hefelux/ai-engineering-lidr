import hashlib
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined

logger = structlog.get_logger()

# Carpeta con las versiones del prompt de estimacion (v1, v2...)
PROMPTS_DIR = Path(__file__).parent / "estimation"


def get_env(folder):
    return Environment(
        loader=FileSystemLoader(folder),
        # Si falta una variable da error (en vez de dejarla vacia)
        undefined=StrictUndefined,
        # Para que los {% if %} no dejen lineas en blanco
        trim_blocks=True,
        lstrip_blocks=True,
    )


# Arma el system y el user prompt a partir de lo que llego del formulario
def render_estimation_prompt(request, version="v1"):
    # Cada version es una carpeta con sus plantillas
    env = get_env(PROMPTS_DIR / version)

    # Los enums se pasan como texto ("phases_table") para compararlos en las plantillas
    variables = {
        "description": request.description,
        "project_type": request.project_type.value,
        "detail_level": request.detail_level.value,
        "output_format": request.output_format.value,
        "reference_projects": request.reference_projects,
        # sin conversacion no hay bloque <project_metadata>
        "project_metadata": None,
    }

    system_prompt = env.get_template("system.j2").render(variables)
    user_prompt = env.get_template("user.j2").render(variables)

    # Hash del prompt final, para saber con que prompt salio cada estimacion
    prompt_hash = hashlib.sha256((system_prompt + user_prompt).encode()).hexdigest()[:12]
    logger.info("prompt_rendered", version=version, prompt_hash=prompt_hash)

    return system_prompt, user_prompt


# Para la conversacion: el system lleva el project_metadata y el mensaje del usuario usa turn.j2
def render_session_prompt(form, transcript, metadata, version="v1"):
    env = get_env(PROMPTS_DIR / version)

    variables = {
        "project_type": form["project_type"],
        "detail_level": form["detail_level"],
        "output_format": form["output_format"],
        "project_metadata": metadata,
        "transcript": transcript,
    }

    system_prompt = env.get_template("system.j2").render(variables)
    user_prompt = env.get_template("turn.j2").render(variables)

    prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()[:12]
    logger.info("session_prompt_rendered", version=version, system_hash=prompt_hash)

    return system_prompt, user_prompt


# Prompt de la segunda llamada, la que actualiza el project_metadata
def render_metadata_prompt(current_metadata, user_message, assistant_message):
    env = get_env(Path(__file__).parent)
    return env.get_template("metadata_extractor.j2").render(
        current_metadata=current_metadata.model_dump_json(indent=2),
        user_message=user_message,
        assistant_message=assistant_message,
    )
