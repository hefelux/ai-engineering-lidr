from app.prompts.loader import render_estimation_prompt
from app.schemas import EstimationRequest

DESCRIPTION = "Una app para reservar canchas de padel, con pagos y recordatorios."


# request valido, cada test cambia solo lo que necesita
def make_request(detail_level="medium", output_format="phases_table"):
    return EstimationRequest(
        description=DESCRIPTION,
        project_type="mobile_app",
        detail_level=detail_level,
        output_format=output_format,
    )


def test_descripcion_va_dentro_de_su_etiqueta():
    system, user = render_estimation_prompt(make_request())
    assert f"<project_description>\n{DESCRIPTION}\n</project_description>" in user


def test_formato_tabla_por_fases():
    system, user = render_estimation_prompt(make_request(output_format="phases_table"))
    assert "| Fase | Tareas | Horas | Perfil |" in system

    system, user = render_estimation_prompt(make_request(output_format="narrative"))
    assert "| Fase | Tareas | Horas | Perfil |" not in system


def test_detallado_pide_supuestos_por_fase():
    system, user = render_estimation_prompt(make_request(detail_level="detailed"))
    assert "supuestos de cada fase" in system

    system, user = render_estimation_prompt(make_request(detail_level="summary"))
    assert "supuestos de cada fase" not in system


def test_system_incluye_los_ejemplos():
    system, user = render_estimation_prompt(make_request())
    assert system.count("<example>") == 2


# ningun {% if %} deja lineas en blanco de mas
def test_sin_lineas_en_blanco_dobles():
    system, user = render_estimation_prompt(make_request())
    assert "\n\n\n" not in system
