import csv
import json
import sys

from app.services import llm_service
from app.services.session_service import EXTRACTOR_SYSTEM
from evals.stress import run


# LLM falso: el extractor guarda el nombre del proyecto y nada mas
def fake_call_llm(system_prompt, messages, max_tokens=2000):
    if system_prompt == EXTRACTOR_SYSTEM:
        text = json.dumps({"project_name": "Orion", "assumed_team_size": None,
                           "mentioned_technologies": [], "agreed_scope": None})
    else:
        text = "Total: 300 horas"
    return {"text": text, "model": "fake", "input_tokens": 100, "output_tokens": 50,
            "cost_usd": 0.001, "latency_ms": 10}


# El runner corre en el mismo proceso y deja una fila por turno con las columnas del evento
def test_runner_en_proceso_deja_el_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_service, "call_llm", fake_call_llm)
    output = tmp_path / "results.csv"
    monkeypatch.setattr(sys, "argv", [
        "run", "--scenarios", "contradiction", "--attachment-sizes", "0,5",
        "--repeats", "1", "--turns", "4", "--output", str(output),
    ])
    import asyncio
    asyncio.run(run.main())

    with open(output, encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 8
    for field in run.OBSERVED_FIELDS:
        assert field in rows[0]
    with_pdf = [r for r in rows if r["attachment_kb"] == "5" and r["turn_index"] == "1"][0]
    assert int(with_pdf["attachments_total_chars"]) > 5000
    # el presupuesto del turno 3 no tiene campo en el metadata: en el turno 4 se pierde
    turn_4 = [r for r in rows if r["turn_index"] == "4"][0]
    assert turn_4["facts_missing"] == "30000"
    assert turn_4["memory_drift_score"] == "0.5"
