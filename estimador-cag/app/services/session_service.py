import json
import logging

from app.prompts.loader import render_metadata_prompt, render_session_prompt
from app.services import llm_service
from app.sessions import ProjectMetadata

logger = logging.getLogger(__name__)

EXTRACTOR_SYSTEM = "Extraes datos de proyectos de software y respondes solo con JSON."


# Segunda llamada al modelo: devuelve el project_metadata actualizado y su costo
# Si algo falla se queda el metadata que habia, la estimacion ya se entrego igual
def update_metadata(current, user_message, assistant_message):
    prompt = render_metadata_prompt(current, user_message, assistant_message)
    try:
        result = llm_service.call_llm(EXTRACTOR_SYSTEM, [{"role": "user", "content": prompt}], max_tokens=500)
        text = result["text"]
        # por si el modelo agrega texto o ``` alrededor del JSON
        start = text.index("{")
        end = text.rindex("}") + 1
        data = json.loads(text[start:end])
        return ProjectMetadata(**data), result["cost_usd"]
    except Exception as e:
        logger.warning(f"No se pudo actualizar el project_metadata: {e}")
        return current, 0.0


# Un turno de la conversacion: arma el prompt, llama al modelo y actualiza historial y metadata
def run_turn(session, form, transcript, version="v1"):
    system_prompt, user_prompt = render_session_prompt(form, transcript, session.metadata, version)

    history = session.history
    history.add_user(user_prompt)
    messages = history.to_messages_list(system_prompt)

    try:
        # Anthropic recibe el system aparte, asi que se saca el primero de la lista
        result = llm_service.call_llm(messages[0]["content"], messages[1:])
    except Exception:
        history.remove_last_user()
        raise

    history.add_assistant(result["text"])

    session.metadata, extractor_cost = update_metadata(session.metadata, transcript, result["text"])

    result["prompt_version"] = version
    result["session_id"] = session.session_id
    result["project_metadata"] = session.metadata
    result["history_turns"] = history.count_turns()
    result["extractor_cost_usd"] = extractor_cost
    return result
