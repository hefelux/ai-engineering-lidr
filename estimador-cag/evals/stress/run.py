"""Corre los escenarios de carga contra el estimador y deja un CSV con una fila por turno.

Uso contra la API levantada:
    uv run python -m evals.stress.run --http http://localhost:8000

Sin --http corre en el mismo proceso (sin levantar uvicorn).

El evento turn_observed se lee de GET /sessions/{id} (campo last_turn) y no de
los logs: es una sola llamada por turno, no depende de donde se escriban los
logs y trae ademas el estado de la sesion que necesita MemoryDriftMetric.
"""

import argparse
import asyncio
import csv
import time
from pathlib import Path

import httpx

from evals.stress.fixtures.build_pdfs import get_pdf
from evals.stress.metrics import CostBudgetMetric, LatencyBudgetMetric, MemoryDriftMetric
from evals.stress.scenarios import SCENARIOS, facts_expected

OBSERVED_FIELDS = [
    "turn_index", "session_id", "enriched_transcript_chars", "attachments_total_chars",
    "messages_in_window", "anchors_count", "summary_chars", "tokens_in", "tokens_out",
    "cost_usd", "latency_ms", "cache_hit_kind", "last_resolved_tier",
    "extractor_cost_usd", "turn_latency_ms",
]
EXTRA_FIELDS = [
    "scenario", "attachment_kb", "repeat", "client_latency_ms",
    "latency_budget_pass", "cost_budget_pass",
    "memory_drift_score", "memory_drift_pass", "facts_expected", "facts_missing",
    "watch_in_metadata", "watch_in_window",
    "attachment_start_in_answer", "attachment_end_in_answer",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Pruebas de carga del CAG")
    parser.add_argument("--http", default=None, help="URL de la API. Si no se pasa, corre en el mismo proceso")
    parser.add_argument("--scenarios", default="growing,pivot,contradiction")
    parser.add_argument("--attachment-sizes", default="0,5,20,50,100")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--turns", type=int, default=20, help="Turnos por conversacion (maximo 20)")
    parser.add_argument("--output", default="evals/stress/results.csv")
    parser.add_argument("--latency-budget-ms", type=int, default=8000)
    parser.add_argument("--cost-budget-usd", type=float, default=0.002)
    parser.add_argument("--parallel", type=int, default=3, help="Conversaciones al mismo tiempo")
    return parser.parse_args()


def make_client(url):
    if url:
        return httpx.AsyncClient(base_url=url, timeout=180)
    # En el mismo proceso: la app de FastAPI sin levantar un servidor
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=180)


# Reintenta si la API o el proveedor fallan un momento (502, 429, red)
async def post_with_retry(client, url, **kwargs):
    for attempt in range(4):
        try:
            response = await client.post(url, **kwargs)
            if response.status_code < 500 and response.status_code != 429:
                return response
        except httpx.HTTPError:
            if attempt == 3:
                raise
        await asyncio.sleep(2 ** attempt * 3)
    return response


def found(words, text):
    text = text.lower()
    return "|".join(word for word in words if word.lower() in text)


# Una conversacion completa: un escenario, un tamaño de adjunto, una repeticion
async def run_conversation(client, args, name, size_kb, repeat, rows):
    scenario = SCENARIOS[name]
    response = await post_with_retry(client, "/sessions")
    session_id = response.json()["session_id"]

    latency_metric = LatencyBudgetMetric(budget_ms=args.latency_budget_ms)
    cost_metric = CostBudgetMetric(budget_usd=args.cost_budget_usd)

    for turn_index, transcript, fact in scenario["turns"][: args.turns]:
        files = []
        # El adjunto va solo en la primera estimacion
        if turn_index == 1 and size_kb > 0:
            pdf = get_pdf(size_kb)
            files = [("attachments", (pdf.name, pdf.read_bytes(), "application/pdf"))]
        data = {
            "transcript": transcript,
            "project_type": scenario["project_type"],
            "detail_level": "summary",
            "output_format": "phases_table",
        }

        started = time.perf_counter()
        response = await post_with_retry(client, f"/sessions/{session_id}/estimate", data=data, files=files)
        client_latency = round((time.perf_counter() - started) * 1000)
        if response.status_code != 200:
            raise RuntimeError(f"{name} turno {turn_index}: la API respondio {response.status_code} {response.text[:200]}")
        answer = response.json()["text"]

        snapshot = (await client.get(f"/sessions/{session_id}")).json()
        observed = snapshot["last_turn"]

        # Memoria: cada hecho que deberia seguir vivo, buscado en summary, anchors y metadata
        expected = facts_expected(name, turn_index)
        missing = []
        for expected_fact in expected:
            if not MemoryDriftMetric(expected_fact).evaluate(snapshot).passed:
                missing.append(expected_fact)
        drift_score = (len(expected) - len(missing)) / len(expected) if expected else 1.0

        row ={field: observed[field] for field in OBSERVED_FIELDS}
        row.update({
            "scenario": name,
            "attachment_kb": size_kb,
            "repeat": repeat,
            "client_latency_ms": client_latency,
            "latency_budget_pass": int(latency_metric.evaluate(observed).passed),
            "cost_budget_pass": int(cost_metric.evaluate(observed).passed),
            "memory_drift_score": round(drift_score, 3),
            "memory_drift_pass": int(len(missing) == 0),
            "facts_expected": "|".join(expected),
            "facts_missing": "|".join(missing),
            "watch_in_metadata": found(scenario["watch"], str(snapshot["project_metadata"])),
            "watch_in_window": found(scenario["watch"], " ".join(m["content"] for m in snapshot["window"])),
            # el dato del principio del PDF (Stripe) y el del final (Kafka)
            "attachment_start_in_answer": int(turn_index == 1 and size_kb > 0 and "stripe" in answer.lower()),
            "attachment_end_in_answer": int(turn_index == 1 and size_kb > 0 and "kafka" in answer.lower()),
        })
        rows.append(row)
        print(f"{name:13} {size_kb:>3} KB rep {repeat} turno {turn_index:>2}: "
              f"{observed['latency_ms']} ms, {observed['tokens_in']} tokens, memoria {drift_score:.2f}", flush=True)


async def main():
    args = parse_args()
    names = args.scenarios.split(",")
    sizes = [int(size) for size in args.attachment_sizes.split(",")]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    jobs = []
    for name in names:
        for size_kb in sizes:
            for repeat in range(1, args.repeats + 1):
                jobs.append((name, size_kb, repeat))

    started = time.perf_counter()
    with open(output, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EXTRA_FIELDS[:3] + OBSERVED_FIELDS + EXTRA_FIELDS[3:])
        writer.writeheader()
        lock = asyncio.Lock()
        limit = asyncio.Semaphore(args.parallel)

        failed = []

        # Si una conversacion falla (por ejemplo, el proveedor no responde), se
        # repite desde cero con una sesion nueva. Asi un error suelto no corta todo.
        async def run_job(job):
            async with limit:
                for attempt in range(1, 4):
                    rows = []
                    try:
                        await run_conversation(client, args, *job, rows)
                        break
                    except Exception as error:
                        print(f"Fallo {job} (intento {attempt}): {error}", flush=True)
                        rows = []
                else:
                    failed.append(job)
                async with lock:
                    writer.writerows(rows)
                    file.flush()

        async with make_client(args.http) as client:
            await asyncio.gather(*(run_job(job) for job in jobs))

    minutes = (time.perf_counter() - started) / 60
    print(f"Listo: {len(jobs) - len(failed)} de {len(jobs)} conversaciones en {minutes:.1f} minutos. CSV en {output}")
    if failed:
        print(f"Fallaron 3 veces: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
