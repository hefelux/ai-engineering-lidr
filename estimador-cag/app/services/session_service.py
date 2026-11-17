import json
import logging
import time

import structlog

from app.prompts.loader import render_metadata_prompt, render_session_prompt
from app.services import llm_service
from app.sessions import ProjectMetadata

logger = logging.getLogger(__name__)
events = structlog.get_logger()

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
def run_turn(session, form, transcript, version="v1", attachments_chars=0):
    started = time.perf_counter()
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

    # Un solo evento con todo lo del turno, asi se arma el CSV de una pasada.
    # Este estimador no tiene resumen, anclas, cache ni tier (la sesion 5 los dejo
    # fuera), por eso esos campos van siempre en 0 o "none".
    session.turn_count += 1
    observed = {
        "turn_index": session.turn_count,
        "session_id": session.session_id,
        "enriched_transcript_chars": len(transcript),
        "attachments_total_chars": attachments_chars,
        "messages_in_window": len(history.messages),
        "anchors_count": 0,
        "summary_chars": 0,
        "tokens_in": result["input_tokens"],
        "tokens_out": result["output_tokens"],
        "cost_usd": result["cost_usd"],
        "latency_ms": result["latency_ms"],
        "cache_hit_kind": "none",
        "last_resolved_tier": "none",
        # extras: la segunda llamada (metadata) y lo que tarda el turno completo
        "extractor_cost_usd": extractor_cost,
        "turn_latency_ms": round((time.perf_counter() - started) * 1000),
    }
    session.last_turn = observed
    events.info("turn_observed", **observed)

    result["prompt_version"] = version
    result["session_id"] = session.session_id
    result["project_metadata"] = session.metadata
    result["history_turns"] = history.count_turns()
    result["extractor_cost_usd"] = extractor_cost
    return result
