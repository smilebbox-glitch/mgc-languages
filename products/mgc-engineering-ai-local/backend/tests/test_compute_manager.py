from pathlib import Path

from app.services.compute_manager import route_for


def test_compute_routes_are_prioritized():
    assert route_for("interactive").priority > route_for("heavy").priority > route_for("background").priority
    assert route_for("heavy").queue == "heavy"


def test_celery_configuration_uses_single_prefetch_and_routes():
    source = (Path(__file__).resolve().parents[1] / "app" / "workers" / "celery_app.py").read_text()
    assert "worker_prefetch_multiplier=1" in source
    assert '"run_design_review": {"queue": "heavy", "priority": 6}' in source
    assert '"sync_all_integrations": {"queue": "background", "priority": 1}' in source
