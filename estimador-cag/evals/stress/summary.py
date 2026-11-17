"""Lee results.csv e imprime en Markdown las tablas del REPORT.md.

Uso: uv run python -m evals.stress.summary [ruta del csv]
"""

import csv
import sys
from collections import defaultdict

from evals.stress.scenarios import TURN_POINTS

SCENARIO_ORDER = ["growing", "pivot", "contradiction"]


def percentile(values, p):
    values = sorted(values)
    if not values:
        return 0
    index = round(p / 100 * (len(values) - 1))
    return values[index]


def mean(values):
    return sum(values) / len(values) if values else 0


def load(path):
    with open(path, encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        for field in ["turn_index", "attachment_kb", "repeat", "tokens_in", "tokens_out", "latency_ms",
                      "turn_latency_ms", "messages_in_window", "attachments_total_chars",
                      "latency_budget_pass", "cost_budget_pass", "memory_drift_pass",
                      "attachment_start_in_answer", "attachment_end_in_answer"]:
            row[field] = int(row[field])
        for field in ["cost_usd", "extractor_cost_usd", "memory_drift_score"]:
            row[field] = float(row[field])
        # costo del turno completo: la estimacion mas la llamada que actualiza el metadata
        row["turn_cost"] = row["cost_usd"] + row["extractor_cost_usd"]
    return rows


def table(headers, lines):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for line in lines:
        out.append("| " + " | ".join(str(value) for value in line) + " |")
    return "\n".join(out)


def summary_table(rows):
    cells = defaultdict(list)
    for row in rows:
        cells[(row["scenario"], row["attachment_kb"])].append(row)
    lines = []
    for name in SCENARIO_ORDER:
        for size in sorted({kb for (s, kb) in cells if s == name}):
            cell = cells[(name, size)]
            latencies = [r["latency_ms"] for r in cell]
            lines.append([
                name, size, len(cell),
                percentile(latencies, 50), percentile(latencies, 95),
                f"{sum(r['turn_cost'] for r in cell):.4f}",
                "0%", "0%",
                f"{mean([r['memory_drift_score'] for r in cell]) * 100:.0f}%",
                f"{mean([r['latency_budget_pass'] for r in cell]) * 100:.0f}%",
                f"{mean([r['cost_budget_pass'] for r in cell]) * 100:.0f}%",
            ])
    return table(["Escenario", "KB", "n", "P50 ms", "P95 ms", "Costo total US$", "Caché exacta",
                  "Caché semántica", "Recall medio", "Dentro de latencia", "Dentro de costo"], lines)


def latency_vs_tokens(rows, step=2000):
    buckets = defaultdict(list)
    for row in rows:
        buckets[row["tokens_in"] // step * step].append(row["latency_ms"])
    lines = []
    for start in sorted(buckets):
        values = buckets[start]
        lines.append([f"{start}-{start + step - 1}", len(values), percentile(values, 50), percentile(values, 95)])
    return table(["tokens_in", "n", "P50 latency_ms", "P95 latency_ms"], lines)


def cost_vs_turn(rows):
    # costo acumulado de cada conversacion, promediado por escenario
    runs = defaultdict(dict)
    for row in rows:
        runs[(row["scenario"], row["attachment_kb"], row["repeat"])][row["turn_index"]] = row["turn_cost"]
    lines = []
    for n in TURN_POINTS:
        line = [n]
        for name in SCENARIO_ORDER:
            totals = []
            for (scenario, kb, rep), costs in runs.items():
                if scenario == name and n in costs:
                    totals.append(sum(costs[t] for t in costs if t <= n))
            line.append(f"{mean(totals):.4f}" if totals else "-")
        lines.append(line)
    return table(["Turno", "growing US$", "pivot US$", "contradiction US$"], lines)


def per_turn_ratio(rows):
    by_turn = defaultdict(list)
    for row in rows:
        by_turn[row["turn_index"]].append(row)
    first = mean([r["turn_cost"] for r in by_turn[1]])
    last_turn = max(by_turn)
    last = mean([r["turn_cost"] for r in by_turn[last_turn]])
    tokens_first = mean([r["tokens_in"] for r in by_turn[1]])
    tokens_last = mean([r["tokens_in"] for r in by_turn[last_turn]])
    return (f"Turno 1: US$ {first:.5f} y {tokens_first:.0f} tokens de entrada en promedio. "
            f"Turno {last_turn}: US$ {last:.5f} y {tokens_last:.0f} tokens. "
            f"El turno {last_turn} cuesta {last / first:.1f} veces el turno 1.")


def recall_vs_n(rows):
    lines = []
    for n in TURN_POINTS:
        line = [n]
        for name in SCENARIO_ORDER:
            cell = [r for r in rows if r["scenario"] == name and r["turn_index"] == n]
            line.append(f"{mean([r['memory_drift_score'] for r in cell]) * 100:.0f}%" if cell else "-")
        lines.append(line)
    return table(["N (turno)", "growing", "pivot", "contradiction"], lines)


def watched(rows, name, words):
    lines = []
    for n in sorted({r["turn_index"] for r in rows if r["scenario"] == name}):
        cell = [r for r in rows if r["scenario"] == name and r["turn_index"] == n]
        line = [n, len(cell)]
        for word in words:
            line.append(f"{mean([word in r['watch_in_metadata'].split('|') for r in cell]) * 100:.0f}%")
            line.append(f"{mean([word in r['watch_in_window'].split('|') for r in cell]) * 100:.0f}%")
        lines.append(line)
    headers = ["Turno", "n"]
    for word in words:
        headers += [f"{word} en metadata", f"{word} en ventana"]
    return table(headers, lines)


def attachments(rows):
    lines = []
    for size in sorted({r["attachment_kb"] for r in rows}):
        cell = [r for r in rows if r["attachment_kb"] == size and r["turn_index"] == 1]
        latencies = [r["latency_ms"] for r in cell]
        lines.append([
            size, len(cell),
            f"{mean([r['attachments_total_chars'] for r in cell]):.0f}",
            f"{mean([r['tokens_in'] for r in cell]):.0f}",
            percentile(latencies, 50), percentile(latencies, 95),
            f"{mean([r['turn_cost'] for r in cell]):.5f}",
            "-" if size == 0 else f"{mean([r['attachment_start_in_answer'] for r in cell]) * 100:.0f}%",
            "-" if size == 0 else f"{mean([r['attachment_end_in_answer'] for r in cell]) * 100:.0f}%",
        ])
    return table(["KB", "n", "Caracteres del adjunto", "tokens_in", "P50 ms", "P95 ms", "Costo turno US$",
                  "Stripe (inicio) en la respuesta", "Kafka (final) en la respuesta"], lines)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "evals/stress/results.csv"
    rows = load(path)
    latencies = [r["latency_ms"] for r in rows]
    print(f"Filas: {len(rows)}. Costo total: US$ {sum(r['turn_cost'] for r in rows):.4f}. "
          f"P50 {percentile(latencies, 50)} ms, P95 {percentile(latencies, 95)} ms.\n")
    print("## Tabla resumen\n")
    print(summary_table(rows))
    print("\n## Latencia contra tokens de entrada\n")
    print(latency_vs_tokens(rows))
    print("\n## Costo acumulado contra turno\n")
    print(cost_vs_turn(rows))
    print("\n" + per_turn_ratio(rows))
    print("\n## Memoria contra N\n")
    print(recall_vs_n(rows))
    print("\n## Pivote: React Native y Flutter\n")
    print(watched(rows, "pivot", ["React Native", "Flutter"]))
    print("\n## Contradicción: presupuestos\n")
    print(watched(rows, "contradiction", ["30000", "80000"]))
    print("\n## Nombre del proyecto (growing)\n")
    print(watched(rows, "growing", ["Nimbus"]))
    print("\n## Adjuntos (turno 1)\n")
    print(attachments(rows))


if __name__ == "__main__":
    main()
