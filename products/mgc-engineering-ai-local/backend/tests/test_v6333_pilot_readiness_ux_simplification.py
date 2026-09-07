from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db.models import Document, DocumentStatus, Project, ProjectMilestone
from app.db.session import Base
from app.services.project_workspace import project_workspace

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src" / "main.tsx"
STYLES = ROOT / "frontend" / "src" / "styles.css"


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_runtime_contract_6333_keeps_database_schema_stable():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_action_center_is_derived_bounded_and_human_controlled():
    db = _db()
    project = Project(code="P6333", name="Pilot", acl_groups=["engineering-a"])
    db.add(project)
    bad = Document(
        filename="failed.pdf", stored_path="/tmp/failed", sha256="3" * 64,
        status=DocumentStatus.failed, project_code="P6333", acl_groups=["engineering-a"],
    )
    db.add(bad)
    db.add(ProjectMilestone(
        project_code="P6333", code="GATE", name="Pilot gate",
        due_at=datetime.now(timezone.utc) - timedelta(days=1), status="in_progress",
    ))
    db.commit()
    out = project_workspace(db, project, {bad.id}, identity_groups=["engineering-a"])
    center = out["action_center"]
    assert center["count"] <= 12
    assert center["critical_count"] >= 1
    assert center["advisory_only"] is True
    assert center["human_decision_required"] is True
    assert center["source"] == "project_readiness_evidence"
    assert all(item["object_id"] for item in center["items"])
    assert center["items"][0]["severity"] == "critical"


def test_primary_navigation_is_reduced_to_five_engineer_workspaces():
    source = FRONTEND.read_text()
    nav = source.split("const NAV:", 1)[1].split("function Viewer", 1)[0]
    for label in ["Главная", "Проекты", "Детали / BOM", "Инструкции", "Поиск / ИИ"]:
        assert label in nav
    for hidden in ["Object 360", "Изменения"]:
        assert hidden not in nav
    assert "Specialist screens remain reachable contextually" in source


def test_project_workspace_uses_progressive_disclosure_and_action_center():
    source = FRONTEND.read_text()
    assert "ProjectFocusWorkspace" in source
    assert 'className="projectAdvanced"' in source
    assert "Полная инженерная картина" in source
    assert "Action Center" in source
    assert "evidence-backed" in source
    assert "onNavigate('changes')" in source
    assert "onNavigate('documents')" in source


def test_pilot_readiness_styles_keep_responsive_layout():
    styles = STYLES.read_text()
    assert "v6.3.34 Pilot Readiness & UX Simplification" in styles
    assert ".workspaceLaunchGrid" in styles
    assert ".projectFocusWorkspace" in styles
    assert "@media(max-width:760px)" in styles


def test_v6333_adds_no_database_migration():
    migrations = ROOT / "backend" / "app" / "db" / "migrations" / "versions"
    assert not list(migrations.glob("*6.3.34*")) if migrations.exists() else True
