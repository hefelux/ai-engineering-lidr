import time

import httpx
import streamlit as st

from app.config import settings

st.set_page_config(page_title="Estimador de proyectos", page_icon="📋")
st.title("Estimador de proyectos")
st.caption("Completa el formulario y te devuelvo la estimación.")

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

# Session state guarda la ultima estimacion entre ejecuciones
if "last_call" not in st.session_state:
    st.session_state.last_call = None

# Con st.form la app no se re-ejecuta en cada cambio, solo al apretar el boton
with st.form("estimation_form"):
    project_type = st.selectbox("Tipo de proyecto", list(PROJECT_TYPES))
    col1, col2 = st.columns(2)
    detail_level = col1.selectbox("Nivel de detalle", list(DETAIL_LEVELS), index=1)
    output_format = col2.selectbox("Formato", list(OUTPUT_FORMATS))
    description = st.text_area(
        "Descripción del proyecto",
        height=200,
        max_chars=2000,
        placeholder="Qué hay que construir, para quién, funcionalidades principales, integraciones, plazos...",
    )
    references = st.text_area(
        "Proyectos parecidos (opcional)",
        height=80,
        placeholder="Uno por línea, con el nombre y las horas separados por una coma. Por ejemplo: Portal de clientes, 400",
    )
    prompt_version = st.selectbox("Versión del prompt", list(PROMPT_VERSIONS))
    submitted = st.form_submit_button("Estimar")

if submitted:
    # Cada linea "Portal de clientes, 400" pasa a {"name": "Portal de clientes", "hours": "400"}
    reference_projects = []
    for line in references.splitlines():
        if "," in line:
            name, hours = line.rsplit(",", 1)
            reference_projects.append({"name": name.strip(), "hours": hours.strip()})

    # El mismo JSON que espera EstimationRequest
    payload = {
        "description": description,
        "project_type": PROJECT_TYPES[project_type],
        "detail_level": DETAIL_LEVELS[detail_level],
        "output_format": OUTPUT_FORMATS[output_format],
        "reference_projects": reference_projects,
    }
    # La version del prompt va en la URL
    params = {"prompt_version": PROMPT_VERSIONS[prompt_version]}

    started = time.perf_counter()
    with st.spinner("Estimando..."):
        try:
            response = httpx.post(f"{settings.api_url}/api/v1/estimate", json=payload, params=params, timeout=120)
        except httpx.HTTPError:
            st.error(f"No pude conectar con la API en {settings.api_url}. Revisa que uvicorn este corriendo.")
            st.stop()

    # 422: la API rechazo los datos antes de llamar al modelo
    if response.status_code == 422:
        st.error(
            "Revisa el formulario. La descripción tiene que tener entre 20 y 2000 caracteres, "
            "y cada proyecto parecido, un nombre y sus horas."
        )
    elif response.status_code != 200:
        st.error(f"La API respondió {response.status_code}: {response.json().get('detail')}")
    else:
        st.session_state.last_call = response.json()
        st.session_state.last_call["seconds"] = time.perf_counter() - started

last = st.session_state.last_call

# Barra lateral: datos de la ultima llamada
with st.sidebar:
    st.header("Última llamada")
    if last:
        st.write(f"Prompt: `{last['prompt_version']}`")
        st.write(f"Modelo: `{last['model']}`")
        col1, col2 = st.columns(2)
        col1.metric("Tokens de entrada", last["input_tokens"])
        col2.metric("Tokens de salida", last["output_tokens"])
        # A lo ancho, porque en media columna el costo no cabe y se corta
        st.metric("Tiempo", f"{last['seconds']:.1f} s")
        st.metric("Costo", f"US$ {last['cost_usd']:.4f}")
    else:
        st.write("Todavía no hay llamadas.")

if last:
    st.markdown(last["text"])
