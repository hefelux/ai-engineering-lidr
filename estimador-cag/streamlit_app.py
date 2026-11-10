import time

import httpx
import streamlit as st

from app.config import settings

st.set_page_config(page_title="Estimador de proyectos", page_icon="📋")
st.title("Estimador de proyectos")
st.caption("Cuéntame el proyecto, sube documentos si tienes y ve ajustando la estimación en la misma conversación.")

# Lo que ve la persona en cada selector y el valor que se manda a la API
PROJECT_TYPES = {
    "App móvil": "mobile_app",
    "Aplicación web SaaS": "web_saas",
    "Herramienta interna": "internal_tool",
    "Pipeline de datos": "data_pipeline",
}
DETAIL_LEVELS = {
    "Resumen": "summary",
    "Medio": "medium",
    "Detallado": "detailed",
}
PROMPT_VERSIONS = {
    "v1: horas fijas": "v1",
    "v2: rango de horas": "v2",
}
OUTPUT_FORMATS = {
    "Tabla por fases": "phases_table",
    "Lista de tareas": "line_items",
    "Texto narrado": "narrative",
}


# Pide una sesion nueva a la API y deja la conversacion en blanco
def start_session():
    try:
        response = httpx.post(f"{settings.api_url}/sessions", timeout=10)
    except httpx.HTTPError:
        st.error(f"No pude conectar con la API en {settings.api_url}. Revisa que uvicorn este corriendo.")
        st.stop()
    if response.status_code != 200:
        st.error(f"La API en {settings.api_url} no pudo crear la sesión (respondió {response.status_code}). ¿Es la API del estimador?")
        st.stop()
    st.session_state.session_id = response.json()["session_id"]
    st.session_state.turns = []
    st.session_state.last_call = None


# Al cargar la pagina por primera vez se crea la sesion
if "session_id" not in st.session_state:
    start_session()

# Conversacion hasta ahora: lo que se escribio, los archivos y la respuesta
for turn in st.session_state.turns:
    with st.chat_message("user"):
        st.write(turn["transcript"])
        if turn["files"]:
            st.caption("Adjuntos: " + ", ".join(turn["files"]))
    with st.chat_message("assistant"):
        st.markdown(turn["answer"])

# Con st.form la app no se re-ejecuta en cada cambio, solo al apretar el boton
with st.form("estimation_form", clear_on_submit=True):
    project_type = st.selectbox("Tipo de proyecto", list(PROJECT_TYPES))
    col1, col2, col3 = st.columns(3)
    detail_level = col1.selectbox("Nivel de detalle", list(DETAIL_LEVELS), index=1)
    output_format = col2.selectbox("Formato", list(OUTPUT_FORMATS))
    prompt_version = col3.selectbox("Versión del prompt", list(PROMPT_VERSIONS))
    transcript = st.text_area(
        "Transcripción o mensaje",
        height=150,
        placeholder="La transcripción de la reunión, o un cambio sobre la estimación anterior (por ejemplo: ¿y si somos 2 personas?)",
    )
    uploaded = st.file_uploader("Documentos (opcional)", type=["pdf", "docx"], accept_multiple_files=True)
    submitted = st.form_submit_button("Enviar")

if submitted:
    if transcript.strip() == "":
        st.error("Escribe la transcripción o un mensaje antes de enviar.")
        st.stop()

    data = {
        "transcript": transcript,
        "project_type": PROJECT_TYPES[project_type],
        "detail_level": DETAIL_LEVELS[detail_level],
        "output_format": OUTPUT_FORMATS[output_format],
    }
    # Cada archivo va con el mismo nombre de campo, asi FastAPI arma la lista
    files = []
    for file in uploaded:
        files.append(("attachments", (file.name, file.getvalue(), file.type)))
    params = {"prompt_version": PROMPT_VERSIONS[prompt_version]}
    url = f"{settings.api_url}/sessions/{st.session_state.session_id}/estimate"

    started = time.perf_counter()
    with st.spinner("Estimando..."):
        try:
            response = httpx.post(url, data=data, files=files, params=params, timeout=180)
        except httpx.HTTPError:
            st.error(f"No pude conectar con la API en {settings.api_url}. Revisa que uvicorn este corriendo.")
            st.stop()

    # 404: la API se reinicio y la sesion ya no existe
    if response.status_code == 404:
        st.warning("La sesión se perdió (seguramente se reinició la API). Empecé una conversación nueva.")
        start_session()
    elif response.status_code != 200:
        st.error(f"La API respondió {response.status_code}: {response.json().get('detail')}")
    else:
        result = response.json()
        result["seconds"] = time.perf_counter() - started
        st.session_state.last_call = result
        st.session_state.turns.append({
            "transcript": transcript,
            "files": [file.name for file in uploaded],
            "answer": result["text"],
        })
        st.rerun()

last = st.session_state.last_call

# Barra lateral: la memoria del proyecto y los datos de la ultima llamada
with st.sidebar:
    if st.button("Nueva conversación"):
        start_session()
        st.rerun()

    st.caption(f"Sesión `{st.session_state.session_id[:8]}`")

    st.header("Project metadata")
    st.caption("Lo que el sistema recuerda del proyecto. Va en el system prompt de cada turno, aparte del historial.")
    if last:
        metadata = last["project_metadata"]
        st.write(f"**Nombre:** {metadata['project_name'] or '-'}")
        st.write(f"**Equipo asumido:** {metadata['assumed_team_size'] or '-'}")
        st.write(f"**Tecnologías:** {', '.join(metadata['mentioned_technologies']) or '-'}")
        st.write(f"**Alcance acordado:** {metadata['agreed_scope'] or '-'}")
        st.write(f"**Turnos en el historial:** {last['history_turns']} de {settings.max_turns}")
    else:
        st.write("Todavía vacío.")

    st.header("Última llamada")
    if last:
        st.write(f"Prompt: `{last['prompt_version']}` · Modelo: `{last['model']}`")
        col1, col2 = st.columns(2)
        col1.metric("Tokens de entrada", last["input_tokens"])
        col2.metric("Tokens de salida", last["output_tokens"])
        st.metric("Tiempo", f"{last['seconds']:.1f} s")
        # Las dos llamadas: la estimacion y la que actualiza el metadata
        st.metric("Costo", f"US$ {last['cost_usd'] + last['extractor_cost_usd']:.4f}")
    else:
        st.write("Todavía no hay llamadas.")
