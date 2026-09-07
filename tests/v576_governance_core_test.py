from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mgc.governance_core import (  # noqa: E402
    audit_event_hash,
    build_governance_core,
    canonical_metadata,
    rls_identity,
)

assert "app" not in sys.modules

metadata = {"z": 2, "a": "Путунхуа"}
encoded = canonical_metadata(metadata)
assert encoded == '{"a": "Путунхуа", "z": 2}'

parts = ["prev", "user.role.change", "7", "user", "9", "req-1", "iphash", encoded]
expected = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
assert audit_event_hash("prev", "user.role.change", 7, "user", "9", "req-1", "iphash", encoded) == expected

user = SimpleNamespace(id=7, role="manager", department="R&D")
identity = rls_identity(user)
assert identity.user_id == "7" and identity.role == "manager" and identity.department == "R&D"
system = rls_identity(system_admin=True)
assert system.user_id == "0" and system.role == "admin" and system.department == "__system__"

class DummyLog:
    pass

class DummyAnchor:
    pass

class CaptureDB:
    def __init__(self):
        self.calls = []
    def execute(self, statement, params):
        self.calls.append((str(statement), dict(params)))

bindings = build_governance_core(
    audit_log_model=DummyLog,
    audit_anchor_model=DummyAnchor,
    database_url="postgresql+psycopg://example/test",
    rls_enabled=True,
    audit_chain_lock_id=123,
    client_key=lambda request: "fingerprint",
)

db = CaptureDB()
bindings.apply_rls_context(db, user)
assert len(db.calls) == 3
assert "app.user_id" in db.calls[0][0] and db.calls[0][1] == {"v": "7"}
assert "app.role" in db.calls[1][0] and db.calls[1][1] == {"v": "manager"}
assert "app.department" in db.calls[2][0] and db.calls[2][1] == {"v": "R&D"}

admin_db = CaptureDB()
bindings.apply_rls_context(admin_db, system_admin=True)
assert [call[1]["v"] for call in admin_db.calls] == ["0", "admin", "__system__"]

noop = build_governance_core(
    audit_log_model=DummyLog,
    audit_anchor_model=DummyAnchor,
    database_url="sqlite:///dev.db",
    rls_enabled=True,
    audit_chain_lock_id=123,
    client_key=lambda request: "fingerprint",
)
noop_db = CaptureDB()
noop.apply_rls_context(noop_db, user)
assert noop_db.calls == []

print("OK: v5.7.6 governance core preserves RLS identity, SQL context and deterministic audit hashing without app.py")
