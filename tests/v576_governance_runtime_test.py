from __future__ import annotations

import inspect
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v576_governance.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "AUTO_CREATE_SCHEMA": "true",
    "APP_ENV": "pilot",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    "MGC_ADMIN_USERNAME": "v576admin",
    "MGC_ADMIN_PASSWORD": "V576AdminPassword!123456",
    "MGC_ADMIN_DISPLAY_NAME": "V576 Admin",
    "OIDC_STATE_SECRET": "v576-governance-secret-32-bytes-0001",
    "TTS_LEGACY_GET_ENABLED": "false",
    "TERM_APPROVAL_REQUIRED": "true",
    "RLS_ENABLED": "true",
    "METRICS_TOKEN": "v576metrics",
    "TTS_CACHE_PERSISTENCE": "ephemeral",
})
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
import app  # noqa: E402
import asgi  # noqa: E402

assert asgi.app is app.app
assert asgi.GOVERNANCE_BINDING_REPORT.ok
assert asgi.GOVERNANCE_BINDING_REPORT.rls_bound
assert asgi.GOVERNANCE_BINDING_REPORT.audit_event_bound
assert asgi.GOVERNANCE_BINDING_REPORT.verifier_available
assert asgi.GOVERNANCE_BINDING_REPORT.audit_model_contract_preserved
assert app.apply_rls_context is app.MGC_GOVERNANCE_BINDINGS.apply_rls_context
assert app.audit_event is app.MGC_GOVERNANCE_BINDINGS.audit_event

# Runtime ordering contract: the extracted auth dependency captured the extracted RLS hook.
closure = inspect.getclosurevars(app.current_user)
assert closure.nonlocals.get("apply_rls_context") is app.apply_rls_context

admin = TestClient(asgi.app)
login = admin.post("/api/login", json={"username": "v576admin", "password": "V576AdminPassword!123456"})
assert login.status_code == 200, login.text
admin_headers = {"X-CSRF-Token": admin.cookies.get("mgc_csrf")}

user = TestClient(asgi.app)
register = user.post(
    "/api/register",
    json={"username": "v576user", "password": "StrongPass123!", "display_name": "Governance User"},
)
assert register.status_code == 200, register.text
user_id = register.json()["user"]["id"]
change = admin.patch(
    f"/api/admin/users/{user_id}/department",
    headers=admin_headers,
    json={"department": "R&D"},
)
assert change.status_code == 200, change.text

with app.SessionLocal() as db:
    core_before = app.verify_audit_chain_core(db)
assert core_before["ok"] is True and core_before["events"] >= 3
endpoint_before = admin.get("/api/admin/audit/verify-chain")
assert endpoint_before.status_code == 200, endpoint_before.text
assert endpoint_before.json() == core_before

# Retention advances AuditAnchor; the extracted verifier must continue from that anchor.
with app.SessionLocal() as db:
    oldest = db.scalars(app.select(app.AuditLog).order_by(app.AuditLog.id.asc()).limit(2)).all()
    assert len(oldest) == 2
    old_at = app.datetime.now(app.timezone.utc) - app.timedelta(days=app.AUDIT_RETENTION_DAYS + 5)
    for row in oldest:
        row.created_at = old_at
    db.commit()
cleanup = admin.post("/api/admin/maintenance/cleanup?dry_run=false", headers=admin_headers)
assert cleanup.status_code == 200, cleanup.text
assert cleanup.json()["counts"]["old_audit"] >= 2
with app.SessionLocal() as db:
    anchor = db.get(app.AuditAnchor, 1)
    assert anchor and anchor.last_deleted_id and len(anchor.last_deleted_hash) == 64
    core_after = app.verify_audit_chain_core(db)
assert core_after["ok"] is True
endpoint_after = admin.get("/api/admin/audit/verify-chain")
assert endpoint_after.status_code == 200 and endpoint_after.json() == core_after

# Deliberate tampering must be detected identically by old endpoint and extracted verifier.
with app.SessionLocal() as db:
    target = db.scalar(app.select(app.AuditLog).order_by(app.AuditLog.id.asc()).limit(1))
    assert target is not None
    target.metadata_json = '{"tampered":true}'
    db.commit()
    tampered_core = app.verify_audit_chain_core(db)
assert tampered_core["ok"] is False and tampered_core["broken_ids"]
tampered_endpoint = admin.get("/api/admin/audit/verify-chain")
assert tampered_endpoint.status_code == 200
assert tampered_endpoint.json() == tampered_core

print("OK: v5.7.6 ASGI governance binding preserves RLS-before-auth ordering, audit chain, retention anchor and tamper detection")
