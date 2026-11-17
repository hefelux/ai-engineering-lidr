# Máster AI Engineering - LIDR

Repositorio con los entregables de cada sesión del curso.

## Ramas por sesión

Listado de ramas de entregables de cada sesión siempre que se requiera.

- session-01: notebook de Colab con las primeras llamadas a la API de Anthropic (carpeta session-01)
- session-02: scaffolding del proyecto, una API con FastAPI que genera estimaciones de software usando CAG (carpeta estimador-cag)
- session-03: chat con Streamlit para el estimador, con streaming
- session-04: el chat pasa a ser un formulario y el prompt vive en plantillas de Jinja2 versionadas, con sus tests
- session-05: el estimador pasa a ser una conversación con memoria (historial con ventana deslizante y project_metadata aparte) y acepta adjuntos PDF y Word
- session-06: pruebas de carga del CAG. Cada turno deja un evento turn_observed, y un runner corre tres conversaciones de 20 turnos con adjuntos de hasta 100 KB. El reporte está en estimador-cag/evals/stress/REPORT.md
