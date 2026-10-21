from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.routers import estimations
from app.services import llm_service
from app.services.llm_service import build_system_prompt

client = TestClient(app)


def test_estructura():
    archivos = [
        "app/main.py",
        "app/config.py",
        "app/routers/estimations.py",
        "app/services/llm_service.py",
        "app/context/examples.py",
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


def test_prompt_incluye_ejemplos():
    prompt = build_system_prompt()
    assert "Ejemplo 1" in prompt
    assert "Ejemplo 2" in prompt


# reemplazo la llamada al LLM por una falsa para no gastar creditos
def fake_estimation(transcription):
    return {
        "estimation": "Estimación de prueba",
        "model": "claude-haiku-4-5",
        "provider": "anthropic",
        "input_tokens": 100,
        "output_tokens": 50,
        "cost_usd": 0.00035,
    }


def test_estimate(monkeypatch):
    monkeypatch.setattr(estimations, "generate_estimation", fake_estimation)
    response = client.post("/api/v1/estimate", json={"transcription": "Necesito una landing page"})
    assert response.status_code == 200
    assert response.json()["estimation"] == "Estimación de prueba"


# si el proveedor falla, el servicio responde 502
def test_estimate_error_llm(monkeypatch):
    def proveedor_caido(api_key):
        raise Exception("sin conexion")

    monkeypatch.setattr(llm_service, "Anthropic", proveedor_caido)
    response = client.post("/api/v1/estimate", json={"transcription": "Necesito una landing page"})
    assert response.status_code == 502
