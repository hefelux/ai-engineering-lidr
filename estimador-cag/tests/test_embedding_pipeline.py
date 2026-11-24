import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError, RateLimitError

from app.embedding_pipeline import embedder as embedder_module
from app.embedding_pipeline import router as router_module
from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import OpenAIEmbedder
from app.embedding_pipeline.schemas import Budget
from app.main import app
from scripts.compare import cosine_similarity

client = TestClient(app)

BUDGETS = json.loads(Path("data/budgets_sample.json").read_text())


# Cliente falso: devuelve un vector de 1536 numeros por texto y anota cada llamada
class FakeEmbeddings:
    def __init__(self, fail_times=0):
        self.calls = []
        self.fail_times = fail_times

    def create(self, model, input):
        self.calls.append(len(input))
        if self.fail_times > 0:
            self.fail_times -= 1
            response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com"))
            raise RateLimitError("rate limit", response=response, body=None)
        data = [SimpleNamespace(embedding=[0.1] * 1536) for _ in input]
        return SimpleNamespace(data=data, usage=SimpleNamespace(total_tokens=10 * len(input)))


def fake_embedder(fail_times=0):
    fake = FakeEmbeddings(fail_times)
    return OpenAIEmbedder(client=SimpleNamespace(embeddings=fake)), fake


def test_un_componente_es_un_fragmento():
    budgets = [Budget(**b) for b in BUDGETS]
    chunks = JSONStructuralChunker().chunk(budgets)

    total_components = sum(len(b.components) for b in budgets)
    assert len(chunks) == total_components

    first = chunks[0]
    assert first.chunk_id == "BUD-2024-001::AUTH-001"
    assert first.text.startswith("[Project: Mobile banking API")
    assert "[Client sector: finance | Year: 2024 | Main tech: ruby_on_rails]" in first.text
    assert "Component: OAuth 2.0 authentication backend" in first.text
    assert first.token_count > 0
    for key in ["budget_id", "component_id", "client_sector", "main_technology", "year", "complexity", "estimated_hours"]:
        assert key in first.metadata


def test_manda_de_a_100_fragmentos():
    budgets = [Budget(**b) for b in BUDGETS]
    chunks = JSONStructuralChunker().chunk(budgets) * 5  # mas de 100 fragmentos
    embedder, fake = fake_embedder()

    embedded = embedder.embed_many(chunks)

    assert len(embedded) == len(chunks)
    assert max(fake.calls) == 100
    assert len(fake.calls) == (len(chunks) + 99) // 100


def test_reintenta_si_la_api_responde_429(monkeypatch):
    waits = []
    monkeypatch.setattr(embedder_module.time, "sleep", waits.append)
    embedder, fake = fake_embedder(fail_times=2)

    assert len(embedder.embed_one("hola")) == 1536
    assert waits == [1, 2]


def test_despues_de_tres_reintentos_sigue_el_error(monkeypatch):
    waits = []
    monkeypatch.setattr(embedder_module.time, "sleep", waits.append)
    embedder, fake = fake_embedder(fail_times=10)

    with pytest.raises(RateLimitError):
        embedder.embed_one("hola")
    assert waits == [1, 2, 4]


def test_ingest_responde_fragmentos_y_estadisticas(monkeypatch):
    monkeypatch.setattr(router_module, "OpenAIEmbedder", lambda: fake_embedder()[0])

    response = client.post("/embeddings/ingest", json={"budgets": BUDGETS[:2]})

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["total_budgets"] == 2
    assert body["stats"]["total_chunks"] == len(body["chunks"])
    assert len(body["chunks"][0]["embedding"]) == 1536


def test_ingest_422_si_el_sector_no_existe():
    budget = json.loads(json.dumps(BUDGETS[0]))
    budget["client_metadata"]["sector"] = "gaming"

    response = client.post("/embeddings/ingest", json={"budgets": [budget]})
    assert response.status_code == 422


def test_ingest_500_con_mensaje_generico(monkeypatch):
    class Broken:
        def embed_many(self, chunks):
            raise APIConnectionError(request=httpx.Request("POST", "https://api.openai.com"))

    monkeypatch.setattr(router_module, "OpenAIEmbedder", lambda: Broken())

    response = client.post("/embeddings/ingest", json={"budgets": BUDGETS[:1]})
    assert response.status_code == 500
    assert response.json() == {"detail": "No se pudieron generar los embeddings."}


def test_coseno_a_mano():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
