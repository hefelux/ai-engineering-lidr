import time

import streamlit as st
from anthropic import Anthropic

from app.config import settings

from app.context.examples import ESTIMATION_EXAMPLES
from app.services.llm_service import MAX_TOKENS, build_system_prompt, calculate_cost

st.set_page_config(page_title="Estimador de proyectos", page_icon="📋")
st.title("Estimador de proyectos")
st.caption("Pega la transcripción de una reunión con un cliente y te devuelvo la estimación.")

if settings.llm_provider != "anthropic":
    st.error("Por ahora solo esta implementado Anthropic. Revisa LLM_PROVIDER en el .env.")
    st.stop()
if not settings.anthropic_api_key:
    st.error("Falta ANTHROPIC_API_KEY en el .env.")
    st.stop()


# Client único para toda la app
@st.cache_resource
def get_client():
    return Anthropic(api_key=settings.anthropic_api_key)


system_prompt = build_system_prompt()

# Session state guarda lo que debe persistir entre ejecuciones
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_call" not in st.session_state:
    st.session_state.last_call = None

# Barra lateral: prompt activo, contexto CAG y metricas de la ultima llamada, etc
with st.sidebar:
    st.header("Contexto")
    with st.expander("System prompt"):
        st.code(system_prompt, language=None, wrap_lines=True)
    st.write(f"Estimaciones de referencia en el contexto: **{len(ESTIMATION_EXAMPLES)}**")

    st.header("Última llamada")
    last = st.session_state.last_call
    if last:
        st.write(f"Modelo: `{last['model']}`")
        col1, col2 = st.columns(2)
        col1.metric("Tokens de entrada", last["input_tokens"])
        col2.metric("Tokens de salida", last["output_tokens"])
        # A lo ancho, porque en media columna el costo no cabe y se corta
        st.metric("Tiempo", f"{last['seconds']:.1f} s")
        st.metric("Costo", f"US$ {last['cost_usd']:.4f}")
    else:
        st.write("Todavía no hay llamadas.")

    if st.button("Nueva conversación"):
        st.session_state.messages = []
        st.session_state.last_call = None
        st.rerun()

# El historial se vuelve a dibujar en cada ejecucion
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Pega la transcripción o haz una pregunta sobre la estimación")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        started = time.perf_counter()
        try:
            # Streaming
            with get_client().messages.stream(
                model=settings.llm_model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                # Conversacion completa
                messages=st.session_state.messages,
            ) as stream:
                answer = st.write_stream(stream.text_stream)
                final = stream.get_final_message()
        except Exception as e:
            st.error(f"No pude llamar al modelo: {e}")
            # Se saca la pregunta que falló para poder reintentarla
            st.session_state.messages.pop()
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.last_call = {
        "model": final.model,
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "seconds": time.perf_counter() - started,
        "cost_usd": calculate_cost(final.usage.input_tokens, final.usage.output_tokens),
    }
    # Re-ejecuta la app para actualizar la barra lateral
    st.rerun()
