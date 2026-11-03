# Estimador CAG

API hecha con FastAPI con un formulario en Streamlit.
Recibe la descripción de un proyecto junto con el tipo, el nivel de detalle y el formato que se quiere, y devuelve una estimación (tareas, horas, equipo y duración) generada con Claude.

El prompt ya no lo escribe la persona. El formulario manda solo los parámetros y el backend arma el prompt con plantillas de Jinja2 versionadas.

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
  -d '{"description": "Una app para reservar canchas de padel con pagos y recordatorios", "project_type": "mobile_app", "detail_level": "medium", "output_format": "phases_table"}'
```

Opciones de cada campo:

- project_type: mobile_app, web_saas, internal_tool, data_pipeline
- detail_level: summary, medium, detailed
- output_format: phases_table, line_items, narrative
- description: entre 20 y 2000 caracteres
- reference_projects (opcional): hasta 5 proyectos parecidos, cada uno con name y hours. Por ejemplo `[{"name": "Portal de clientes", "hours": 400}]`

La versión del prompt se elige en la URL, con `?prompt_version=v1` o `?prompt_version=v2`. Si no se manda, se usa v1.

Si algo no cumple, la API responde 422 y no llama al modelo.

## Formulario con Streamlit

Con la API corriendo, en otra terminal:

```
uv run streamlit run streamlit_app.py
```

Se abre en http://localhost:8501. El formulario hace POST a la API (API_URL en el .env, por defecto http://localhost:8000).
En el formulario también se pueden poner proyectos parecidos (uno por línea, nombre y horas separados por una coma) y elegir la versión del prompt.
En la barra lateral están la versión del prompt, el modelo, los tokens, el tiempo y el costo de la última llamada.

## Prompts

Los prompts están en app/prompts/estimation, una carpeta por versión:

- v1/system.j2: rol, reglas, un bloque según el formato y otro según el nivel de detalle, y al final los ejemplos
- v1/user.j2: el tipo de proyecto, la descripción dentro de `<project_description>` y, si vienen, los proyectos de referencia (un `{% for %}` que escribe una línea por proyecto)
- v1/examples.j2: las estimaciones de ejemplo (contexto CAG)
- v2/: igual que v1, pero pide las horas como rango (mínimo y máximo) en vez de un número fijo

Para probar un cambio en el prompt se crea una carpeta nueva en vez de tocar la que funciona, y se comparan las dos con el mismo formulario.

app/prompts/loader.py junta todo con `render_estimation_prompt(request, version="v1")` y devuelve el system y el user por separado.
Usa StrictUndefined, así que si a una plantilla le falta una variable da error en vez de mandar el prompt con un hueco.

Cada vez que arma un prompt deja una línea en el log con structlog:

```
[info     ] prompt_rendered    prompt_hash=e62955a35cb9 version=v2
```

El hash es una huella del prompt final. Si cambia una sola coma, cambia el hash, así se puede saber con qué prompt exacto salió cada estimación.

## Tests

```
uv run pytest
```

Revisan la estructura de carpetas, /health, /docs y el endpoint de estimación (con una respuesta falsa para no gastar créditos, y que rechace datos inválidos con 422).

En tests/prompts/test_estimation_v1.py están los tests de las plantillas. No llaman a ninguna API y tardan milisegundos:

- la descripción aparece tal cual dentro de `<project_description>`
- con phases_table el system trae el encabezado de la tabla y con narrative no
- con detailed se piden los supuestos de cada fase y con summary no
- van los dos ejemplos y no quedan líneas en blanco de más

En tests/prompts/test_estimation_v2.py, que la v2 pide rangos y la v1 no, que el `{% for %}` escribe cada proyecto de referencia (y nada si no hay), y que el log trae la versión y el hash.

También corren en GitHub Actions en cada push.

## Estructura

- app/main.py: crea la app y el endpoint /health
- app/config.py: lee las variables del .env
- app/schemas.py: lo que entra (EstimationRequest) y lo que sale (EstimationResponse)
- app/routers/estimations.py: endpoint POST /api/v1/estimate
- app/prompts/loader.py: arma el system y el user prompt desde las plantillas
- app/prompts/estimation/v1/ y v2/: plantillas del prompt, una carpeta por versión
- app/services/llm_service.py: llama a Claude y calcula el costo
- streamlit_app.py: formulario con Streamlit
