from evals.stress.metrics import CostBudgetMetric, LatencyBudgetMetric, MemoryDriftMetric
from evals.stress.scenarios import SCENARIOS, facts_expected

SNAPSHOT = {
    "summary": "",
    "anchors": [],
    "project_metadata": {
        "project_name": "Nimbus",
        "assumed_team_size": 2,
        "mentioned_technologies": ["React", "PostgreSQL"],
        "agreed_scope": None,
    },
    "window": [{"role": "user", "content": "El presupuesto es de 30000 euros"}],
}


# Una que pasa
def test_latencia_dentro_del_presupuesto():
    result = LatencyBudgetMetric(budget_ms=8000).evaluate({"latency_ms": 3200})
    assert result.passed and result.score == 1.0
    assert result.name == "latency_budget"


# Una que falla
def test_costo_sobre_el_presupuesto():
    result = CostBudgetMetric(budget_usd=0.002).evaluate({"cost_usd": 0.0031})
    assert not result.passed and result.score == 0.0


# Datos en el limite: justo en el presupuesto cuenta como dentro
def test_justo_en_el_limite():
    assert LatencyBudgetMetric(budget_ms=8000).evaluate({"latency_ms": 8000}).passed
    assert CostBudgetMetric(budget_usd=0.002).evaluate({"cost_usd": 0.002}).passed


def test_memoria_encuentra_el_hecho_sin_mayusculas():
    result = MemoryDriftMetric("nimbus").evaluate(SNAPSHOT)
    assert result.passed and "metadata" in result.details


def test_memoria_no_lo_encuentra():
    result = MemoryDriftMetric("Flutter").evaluate(SNAPSHOT)
    assert not result.passed and result.score == 0.0


# Un hecho que solo sigue en la ventana no cuenta, salvo que se pida mirar ahi
def test_memoria_solo_en_la_ventana():
    assert not MemoryDriftMetric("30000").evaluate(SNAPSHOT).passed
    assert MemoryDriftMetric("30000", where=["metadata", "window"]).evaluate(SNAPSHOT).passed


def test_snapshot_vacio_no_rompe():
    result = MemoryDriftMetric("Nimbus").evaluate({})
    assert not result.passed


def test_los_tres_perfiles_tienen_20_turnos():
    for scenario in SCENARIOS.values():
        assert [t[0] for t in scenario["turns"]] == list(range(1, 21))


def test_el_presupuesto_viejo_deja_de_contar():
    assert "30000" in facts_expected("contradiction", 5)
    assert "30000" not in facts_expected("contradiction", 9)
    assert "80000" in facts_expected("contradiction", 9)
    assert facts_expected("growing", 1) == []
