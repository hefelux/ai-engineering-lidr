"""Metricas de las pruebas de carga.

Van aqui y no en evals/metrics.py porque este estimador no tiene un framework
de evals previo (la sesion 5 no lo pidio), y porque miran el evento
turn_observed y el estado de la sesion, no la estimacion en si.

Todas son deterministas: comparan numeros o buscan texto, sin LLM ni embeddings.
"""

import json
from dataclasses import dataclass


@dataclass
class MetricResult:
    name: str
    score: float
    passed: bool
    details: str


class LatencyBudgetMetric:
    """1.0 si latency_ms <= budget_ms; 0.0 si no."""

    def __init__(self, budget_ms: int):
        self.budget_ms = budget_ms

    def evaluate(self, observation) -> MetricResult:
        latency = observation["latency_ms"]
        passed = latency <= self.budget_ms
        return MetricResult(
            name="latency_budget",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=f"{latency} ms (presupuesto {self.budget_ms} ms)",
        )


class CostBudgetMetric:
    """1.0 si cost_usd <= budget_usd; 0.0 si no."""

    def __init__(self, budget_usd: float):
        self.budget_usd = budget_usd

    def evaluate(self, observation) -> MetricResult:
        cost = observation["cost_usd"]
        passed = cost <= self.budget_usd
        return MetricResult(
            name="cost_budget",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=f"US$ {cost} (presupuesto US$ {self.budget_usd})",
        )


class MemoryDriftMetric:
    """1.0 si el hecho aparece en summary, anchors o project_metadata del snapshot; 0.0 si no.

    Busca el texto sin distinguir mayusculas. where puede incluir tambien
    "window" (los mensajes que siguen en la ventana) para ver si el hecho
    sobrevive solo porque todavia no salio del historial.
    """

    def __init__(self, fact: str, where: list[str] = ["summary", "anchors", "metadata"]):
        self.fact = fact
        self.where = where

    def evaluate(self, session_snapshot) -> MetricResult:
        fact = self.fact.lower()
        found_in = []
        for place in self.where:
            if fact in _text_of(session_snapshot, place).lower():
                found_in.append(place)
        passed = len(found_in) > 0
        if passed:
            details = f"'{self.fact}' esta en: {', '.join(found_in)}"
        else:
            details = f"'{self.fact}' no aparece en {', '.join(self.where)}"
        return MetricResult(
            name="memory_drift",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=details,
        )


# El texto de una parte del snapshot, para buscar dentro
def _text_of(snapshot, place):
    if place == "summary":
        return snapshot.get("summary") or ""
    if place == "anchors":
        return " ".join(snapshot.get("anchors") or [])
    if place == "metadata":
        return json.dumps(snapshot.get("project_metadata") or {}, ensure_ascii=False)
    if place == "window":
        return " ".join(message["content"] for message in snapshot.get("window") or [])
    return ""
