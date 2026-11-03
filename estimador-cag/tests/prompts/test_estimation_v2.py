from structlog.testing import capture_logs

from app.prompts.loader import render_estimation_prompt
from app.schemas import EstimationRequest

DESCRIPTION = "Una app para reservar canchas de padel, con pagos y recordatorios."


# request valido, cada test cambia solo lo que necesita
def make_request(output_format="phases_table", reference_projects=[]):
    return EstimationRequest(
        description=DESCRIPTION,
        project_type="mobile_app",
        detail_level="medium",
        output_format=output_format,
        reference_projects=reference_projects,
    )


def test_v2_pide_rangos_de_horas():
    system, user = render_estimation_prompt(make_request(), version="v2")
    assert "| Fase | Tareas | Horas (mín-máx) | Perfil |" in system

    # la v1 sigue pidiendo horas fijas
    system, user = render_estimation_prompt(make_request(), version="v1")
    assert "Horas (mín-máx)" not in system


def test_v2_incluye_los_ejemplos():
    system, user = render_estimation_prompt(make_request(), version="v2")
    assert system.count("<example>") == 2


# el {% for %} escribe una linea por cada proyecto de referencia
def test_proyectos_de_referencia():
    proyectos = [
        {"name": "Portal de clientes", "hours": 400},
        {"name": "App de turnos", "hours": 250},
    ]
    for version in ["v1", "v2"]:
        system, user = render_estimation_prompt(make_request(reference_projects=proyectos), version)
        assert "- Portal de clientes: 400 horas" in user
        assert "- App de turnos: 250 horas" in user


# sin proyectos de referencia no aparece el bloque
def test_sin_proyectos_de_referencia():
    system, user = render_estimation_prompt(make_request(), version="v2")
    assert "<reference_projects>" not in user
    assert "\n\n\n" not in user


# el loader deja en el log la version y el hash del prompt
def test_log_con_version_y_hash():
    with capture_logs() as logs:
        render_estimation_prompt(make_request(), version="v2")
        render_estimation_prompt(make_request(output_format="narrative"), version="v2")

    assert logs[0]["event"] == "prompt_rendered"
    assert logs[0]["version"] == "v2"
    assert len(logs[0]["prompt_hash"]) == 12
    # prompts distintos tienen hash distinto
    assert logs[0]["prompt_hash"] != logs[1]["prompt_hash"]
