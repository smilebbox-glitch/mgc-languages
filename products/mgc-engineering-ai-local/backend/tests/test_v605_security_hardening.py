from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core import security
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v605_schema
from app.db.session import Base
from app.db.models import AuditEvent
from app.services import enterprise_security


def test_v605_schema_marker_is_additive_and_idempotent():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_v605_schema(engine)
    ensure_v605_schema(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.0.5"


def _security_cfg(**overrides):
    base = dict(
        app_env="prod", auth_mode="trusted_headers", engineer_only_access=True,
        engineer_access_group_set={"engineering-ai-users"}, engineering_admin_group_set={"engineering-ai-admins"},
        allow_trusted_headers_in_prod=False, trusted_proxy_secret="", allow_api_key_auth_in_prod=False,
        api_key="change-me", api_key_group_set=set(), oidc_audience="mgc", oidc_issuer="https://idp.example",
        oidc_jwks_url="https://idp.example/jwks", oidc_allowed_jwks_host_set={"idp.example"},
        oidc_allowed_algorithm_set={"RS256"}, oidc_required_claim_set={"exp","iat","sub"},
        oidc_required_acr_set=set(), oidc_clock_skew_seconds=60, oidc_user_claim="sub", oidc_groups_claim="groups",
        allow_insecure_oidc_in_prod=False,
    )
    base.update(overrides); return SimpleNamespace(**base)


def test_trusted_headers_are_disabled_in_production_by_default(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: _security_cfg())
    with pytest.raises(HTTPException) as exc:
        security.get_identity(x_forwarded_user="alice", x_forwarded_groups="engineering-ai-users")
    assert exc.value.status_code == 503


def test_trusted_headers_require_proxy_secret_when_explicitly_enabled(monkeypatch):
    cfg=_security_cfg(allow_trusted_headers_in_prod=True, trusted_proxy_secret="dummy-proxy-secret-for-test-only")
    monkeypatch.setattr(security, "get_settings", lambda: cfg)
    with pytest.raises(HTTPException) as exc:
        security.get_identity(x_forwarded_user="alice", x_forwarded_groups="engineering-ai-users", x_mgc_proxy_secret="wrong")
    assert exc.value.status_code == 401
    identity=security.get_identity(x_forwarded_user="alice", x_forwarded_groups="engineering-ai-users", x_mgc_proxy_secret=cfg.trusted_proxy_secret)
    assert identity.user == "alice" and "engineering-ai-users" in identity.groups


def _enterprise_cfg():
    return SimpleNamespace(
        app_env="prod", engineer_only_access=True, allow_api_key_auth_in_prod=False, auth_mode="oidc",
        oidc_issuer="https://idp.example", oidc_jwks_url="https://idp.example/jwks", oidc_audience="mgc-api",
        allow_insecure_oidc_in_prod=False, oidc_allowed_algorithm_set={"RS256","ES256"}, oidc_clock_skew_seconds=60,
        allow_trusted_headers_in_prod=False, trusted_proxy_secret="", cors_list=["https://mgc.example"],
        audit_retention_days=3650, audit_min_retention_days=365, security_require_tls_edge=True,
        api_key="not-a-real-runtime-secret-for-test", neo4j_password="not-a-real-runtime-secret-for-test", minio_secret_key="not-a-real-runtime-secret-for-test",
        audit_export_max_rows=5000,
    )


def test_security_posture_passes_hardened_policy(monkeypatch):
    monkeypatch.setattr(enterprise_security, "get_settings", _enterprise_cfg)
    out=enterprise_security.security_posture()
    assert out["status"] == "PASS"
    assert out["critical_failed_count"] == 0


def test_audit_export_redacts_sensitive_detail_keys_and_hashes(monkeypatch):
    engine=create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine); db=Session()
    db.add(AuditEvent(user="alice", action="TEST", details={"token":"super-secret-token", "safe":"ok"}, created_at=datetime.now(timezone.utc)))
    db.commit()
    monkeypatch.setattr(enterprise_security, "get_settings", _enterprise_cfg)
    payload,manifest=enterprise_security.build_audit_export(db)
    text_payload=payload.decode()
    assert "super-secret-token" not in text_payload
    assert "[REDACTED]" in text_payload and '"safe":"ok"' in text_payload
    assert len(manifest["sha256"]) == 64 and len(manifest["chain_head"]) == 64


def test_audit_retention_requires_explicit_confirmation(monkeypatch):
    engine=create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine); db=Session()
    old=datetime.now(timezone.utc)-timedelta(days=4000)
    db.add(AuditEvent(user="alice", action="OLD", details={}, created_at=old)); db.commit()
    monkeypatch.setattr(enterprise_security, "get_settings", _enterprise_cfg)
    preview=enterprise_security.audit_retention_preview(db)
    assert preview["eligible_rows"] == 1
    with pytest.raises(ValueError): enterprise_security.apply_audit_retention(db, confirm="yes", actor="admin")
    out=enterprise_security.apply_audit_retention(db, confirm="PURGE_AUDIT", actor="admin")
    assert out["deleted_rows"] == 1
    assert db.query(AuditEvent).filter(AuditEvent.action=="AUDIT_RETENTION_APPLIED").count() == 1


def test_enterprise_compose_and_tls_controls_exist():
    root=Path(__file__).resolve().parents[2]
    compose=(root/'docker-compose.enterprise-security.yml').read_text()
    nginx=(root/'ops/enterprise-edge/nginx.conf').read_text()
    assert 'AUTO_MIGRATE_SCHEMA: "false"' in compose
    assert 'MGC_RUNTIME_DATABASE_URL' in compose and 'MGC_MIGRATION_DATABASE_URL' in compose
    assert 'ssl_protocols TLSv1.2 TLSv1.3' in nginx
    assert 'ssl_verify_client on' in nginx and 'Strict-Transport-Security' in nginx
