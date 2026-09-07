
from app.db import models  # noqa: F401
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect, text

from app.core import operational_health
from app.db.bootstrap import bootstrap_schema, migration_lock
from app.db.session import Base
from app.db.migrations import ensure_v601_schema
from app.api import health_routes


def test_v601_schema_state_is_additive_and_idempotent():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v601_schema(engine)
    ensure_v601_schema(engine)
    assert "mgc_schema_state" in set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.0.1"


def test_bootstrap_schema_records_operational_state_on_sqlite():
    engine = create_engine("sqlite:///:memory:")
    bootstrap_schema(engine, Base.metadata)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == operational_health.EXPECTED_SCHEMA_VERSION
    # SQLite/dev lock path is intentionally non-blocking.
    with migration_lock(engine):
        pass


def _cfg(tmp_path: Path, *, require_redis=True, require_qdrant=True):
    storage = tmp_path / "storage"
    storage.mkdir()
    return SimpleNamespace(
        app_name="MGC test",
        air_gapped_mode=True,
        storage_dir=storage,
        redis_url="redis://unused",
        qdrant_url="http://unused",
        health_timeout_seconds=0.1,
        readiness_require_redis=require_redis,
        readiness_require_qdrant=require_qdrant,
        graph_enabled=False,
        object_store_enabled=False,
    )


def test_readiness_fails_closed_for_required_dependency(monkeypatch, tmp_path):
    monkeypatch.setattr(operational_health, "get_settings", lambda: _cfg(tmp_path))
    monkeypatch.setattr(operational_health, "_database", lambda: None)
    monkeypatch.setattr(operational_health, "_storage", lambda: None)
    monkeypatch.setattr(operational_health, "_redis", lambda: None)
    def broken_qdrant():
        raise RuntimeError("secret internal URL must not leak")
    monkeypatch.setattr(operational_health, "_qdrant", broken_qdrant)
    out = operational_health.readiness_snapshot()
    assert out["status"] == "not_ready"
    qdrant = next(x for x in out["checks"] if x["name"] == "qdrant")
    assert qdrant["required"] is True and qdrant["status"] == "failed"
    assert "secret" not in str(out).lower()
    assert "unused" not in str(out).lower()


def test_optional_dependency_can_degrade_without_blocking(monkeypatch, tmp_path):
    monkeypatch.setattr(operational_health, "get_settings", lambda: _cfg(tmp_path, require_qdrant=False))
    monkeypatch.setattr(operational_health, "_database", lambda: None)
    monkeypatch.setattr(operational_health, "_storage", lambda: None)
    monkeypatch.setattr(operational_health, "_redis", lambda: None)
    monkeypatch.setattr(operational_health, "_qdrant", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    out = operational_health.readiness_snapshot()
    assert out["status"] == "ready"
    assert out["policy"]["local_ai_is_readiness_gate"] is False


def test_ready_endpoint_uses_503_for_not_ready(monkeypatch):
    monkeypatch.setattr(health_routes, "readiness_snapshot", lambda: {"status": "not_ready", "checks": []})
    response = health_routes.health_ready()
    assert response.status_code == 503


def test_worker_healthcheck_overrides_api_healthcheck():
    root = Path(__file__).resolve().parents[2]
    for name in ["docker-compose.yml", "docker-compose.airgap.yml", "docker-compose.connected.yml"]:
        text_value = (root / name).read_text(encoding="utf-8")
        assert 'test: ["CMD", "python", "-m", "app.workers.healthcheck"]' in text_value
    dockerfile = (root / "backend/Dockerfile").read_text(encoding="utf-8")
    assert "/api/v1/health/ready" in dockerfile


def test_dr_scripts_do_not_package_env_file():
    root = Path(__file__).resolve().parents[2]
    backup = (root / "scripts/backup_core.sh").read_text(encoding="utf-8")
    assert "postgres.dump" in backup and "qdrant.snapshot" in backup and "storage.tar.gz" in backup
    assert "cp .env" not in backup and "tar" in backup
    restore = (root / "scripts/restore_core.sh").read_text(encoding="utf-8")
    assert "MGC_RESTORE_CONFIRM" in restore
    assert "sha256sum -c" in restore
    assert "/health/ready" in restore
