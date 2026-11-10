import json
from pathlib import Path

import httpx
import pytest

from app.config import settings
from app.main import app
from app.services import llm_service
from app.services.session_service import EXTRACTOR_SYSTEM

PDF = Path(__file__).parent / "fixtures" / "requisitos.pdf"

# Los campos del formulario que acompanan a la transcripcion
FORM = {"project_type": "mobile_app", "detail_level": "summary", "output_format": "line_items"}

TECHNOLOGIES = ["Flutter", "Stripe", "SAP"]


# LLM falso para no gastar creditos. Guarda cada llamada para poder revisar que se mando.
# - si es la llamada del extractor devuelve un JSON con lo que encuentra en el prompt
# - si es la estimacion, la respuesta cambia si el mensaje habla de Stripe
class FakeLLM:
    def __init__(self):
        self.estimate_calls = []

    def __call__(self, system_prompt, messages, max_tokens=2000):
        last = messages[-1]["content"]

        if system_prompt == EXTRACTOR_SYSTEM:
            data = {"project_name": None, "assumed_team_size": None, "mentioned_technologies": [], "agreed_scope": None}
            if "Reservas Padel Club" in last:
                data["project_name"] = "Reservas Padel Club"
            if "3 personas" in last:
                data["assumed_team_size"] = 3
            for technology in TECHNOLOGIES:
                if technology in last:
                    data["mentioned_technologies"].append(technology)
            text = json.dumps(data)
        else:
            self.estimate_calls.append({"system": system_prompt, "messages": messages})
            if "Stripe" in last:
                text = "Total: 380 horas (incluye pagos con Stripe)"
            else:
                text = "Total: 300 horas"

        return {"text": text, "model": "fake", "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0}


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm_service, "call_llm", fake)
    return fake


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def new_session(client):
    response = await client.post("/sessions")
    assert response.status_code == 200
    return response.json()["session_id"]


async def send_turn(client, session_id, transcript, files=None):
    data = dict(FORM)
    data["transcript"] = transcript
    return await client.post(f"/sessions/{session_id}/estimate", data=data, files=files)


# Dos peticiones en la misma sesion: el project_metadata se va completando y no se pierde lo de antes
@pytest.mark.anyio
async def test_metadata_se_actualiza_entre_turnos(fake_llm):
    async with make_client() as client:
        session_id = await new_session(client)

        first = await send_turn(client, session_id, "Queremos la app Reservas Padel Club para reservar canchas.")
        assert first.status_code == 200
        metadata = first.json()["project_metadata"]
        assert metadata["project_name"] == "Reservas Padel Club"
        assert metadata["assumed_team_size"] is None

        second = await send_turn(client, session_id, "Seriamos 3 personas y la haremos con Flutter.")
        assert second.status_code == 200
        metadata = second.json()["project_metadata"]
        assert metadata["project_name"] == "Reservas Padel Club"
        assert metadata["assumed_team_size"] == 3
        assert metadata["mentioned_technologies"] == ["Flutter"]

    # en la primera llamada el bloque va vacio y en la segunda ya lleva el nombre
    first_system = fake_llm.estimate_calls[0]["system"]
    second_system = fake_llm.estimate_calls[1]["system"]
    assert "<project_metadata>\n</project_metadata>" in first_system
    assert "Nombre del proyecto: Reservas Padel Club" in second_system


# Con el PDF adjunto la estimacion cambia, porque el texto del PDF llega al modelo
@pytest.mark.anyio
async def test_pdf_adjunto_cambia_la_estimacion(fake_llm):
    transcript = "Una app para reservar canchas de padel en varios clubes."

    async with make_client() as client:
        without_pdf = await send_turn(client, await new_session(client), transcript)

        files = [("attachments", ("requisitos.pdf", PDF.read_bytes(), "application/pdf"))]
        with_pdf = await send_turn(client, await new_session(client), transcript, files)

    assert without_pdf.status_code == 200
    assert with_pdf.status_code == 200
    assert without_pdf.json()["text"] == "Total: 300 horas"
    assert with_pdf.json()["text"] == "Total: 380 horas (incluye pagos con Stripe)"
    assert "Stripe" in with_pdf.json()["project_metadata"]["mentioned_technologies"]

    # el texto del PDF va despues del separador, dentro del mensaje del usuario
    user_message = fake_llm.estimate_calls[1]["messages"][-1]["content"]
    assert "--- attachment: requisitos.pdf ---" in user_message
    assert "SAP Business One" in user_message


# 8 turnos en la misma sesion: al modelo nunca le llegan mas de MAX_TURNS
@pytest.mark.anyio
async def test_ventana_deslizante(fake_llm):
    async with make_client() as client:
        session_id = await new_session(client)
        for number in range(1, 9):
            response = await send_turn(client, session_id, f"Mensaje numero {number}")
            assert response.status_code == 200

    assert response.json()["history_turns"] == settings.max_turns

    for call in fake_llm.estimate_calls:
        user_messages = [m for m in call["messages"] if m["role"] == "user"]
        assert len(user_messages) <= settings.max_turns
        # el system nunca viaja dentro de messages, va aparte
        assert call["messages"][0]["role"] == "user"

    # en la ultima llamada ya no estan los dos primeros mensajes
    last_call = json.dumps(fake_llm.estimate_calls[-1]["messages"])
    assert "Mensaje numero 1\\n" not in last_call
    assert "Mensaje numero 2\\n" not in last_call
    assert "Mensaje numero 3\\n" in last_call


@pytest.mark.anyio
async def test_sesion_que_no_existe(fake_llm):
    async with make_client() as client:
        response = await send_turn(client, "no-existe", "Hola")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_adjunto_no_soportado(fake_llm):
    async with make_client() as client:
        session_id = await new_session(client)
        files = [("attachments", ("notas.txt", b"hola", "text/plain"))]
        response = await send_turn(client, session_id, "Una app de reservas", files)
    assert response.status_code == 415
    # la pregunta rechazada no queda en el historial
    assert fake_llm.estimate_calls == []
