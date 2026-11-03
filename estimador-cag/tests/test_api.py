from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.routers import estimations
from app.services import llm_service

client = TestClient(app)


def test_estructura():
    archivos = [
        "app/main.py",
        "app/config.py",
        "app/routers/estimations.py",
        "app/services/llm_service.py",
        "app/schemas.py",
        "app/prompts/loader.py",
        "app/prompts/estimation/v1/system.j2",
        "app/prompts/estimation/v1/user.j2",
        "app/prompts/estimation/v1/examples.j2",
        "app/prompts/estimation/v2/system.j2",
        "app/prompts/estimation/v2/user.j2",
        "app/prompts/estimation/v2/examples.j2",
        ".env.example",
    ]
    for archivo in archivos:
        assert Path(archivo).exists(), f"falta {archivo}"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200


# Lo que manda el formulario
FORM = {
    "description": "Necesito una landing page con formulario de contacto",
    "project_type": "web_saas",
    "detail_level": "summary",
    "output_format": "line_items",
}


# reemplazo la llamada al LLM por una falsa para no gastar creditos
def fake_estimation(request, version="v1"):
    return {
        "text": "Estimación de prueba",
        "prompt_version": version,
        "model": "claude-haiku-4-5",
        "input_tokens": 100,
        "output_tokens": 50,
        "cost_usd": 0.00035,
    }


def test_estimate(monkeypatch):
    monkeypatch.setattr(estimations, "generate_estimation", fake_estimation)
    response = client.post("/api/v1/estimate", json=FORM)
    assert response.status_code == 200
    assert response.json()["text"] == "Estimación de prueba"
    assert response.json()["prompt_version"] == "v1"


# si la descripcion es muy corta o el formato no existe, 422 y no se llama al modelo
def test_estimate_datos_invalidos(monkeypatch):
    monkeypatch.setattr(estimations, "generate_estimation", fake_estimation)

    corta = dict(FORM)
    corta["description"] = "Una landing"
    assert client.post("/api/v1/estimate", json=corta).status_code == 422

    formato_raro = dict(FORM)
    formato_raro["output_format"] = "excel"
    assert client.post("/api/v1/estimate", json=formato_raro).status_code == 422


# la version del prompt se elige en la URL, si no existe da 422
def test_estimate_prompt_version(monkeypatch):
    monkeypatch.setattr(estimations, "generate_estimation", fake_estimation)

    response = client.post("/api/v1/estimate?prompt_version=v2", json=FORM)
    assert response.status_code == 200
    assert response.json()["prompt_version"] == "v2"

    response = client.post("/api/v1/estimate?prompt_version=v3", json=FORM)
    assert response.status_code == 422


# reference_projects es opcional, pero si viene tiene que tener nombre y horas mayores a 0
def test_estimate_reference_projects(monkeypatch):
    monkeypatch.setattr(estimations, "generate_estimation", fake_estimation)

    con_referencia = dict(FORM)
    con_referencia["reference_projects"] = [{"name": "Portal de clientes", "hours": 400}]
    assert client.post("/api/v1/estimate", json=con_referencia).status_code == 200

    horas_en_cero = dict(FORM)
    horas_en_cero["reference_projects"] = [{"name": "Portal de clientes", "hours": 0}]
    assert client.post("/api/v1/estimate", json=horas_en_cero).status_code == 422


# si el proveedor falla, el servicio responde 502
def test_estimate_error_llm(monkeypatch):
    def proveedor_caido(api_key):
        raise Exception("sin conexion")

    monkeypatch.setattr(llm_service, "Anthropic", proveedor_caido)
    # en GitHub Actions no hay .env, asi que el proveedor se fija aca
    monkeypatch.setattr(llm_service.settings, "llm_provider", "anthropic")
    response = client.post("/api/v1/estimate", json=FORM)
    assert response.status_code == 502
