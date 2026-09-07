from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.migrations import ensure_v607_schema
from app.db.models import PilotStudy, PilotUsabilityIssue, Project
from app.services.ux_simplification import build_role_landing, normalize_role
from app.services.pilot_acceptance import evaluate_pilot


def test_v607_migration_marker_and_idempotency():
    eng=create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng)
    ensure_v607_schema(eng); ensure_v607_schema(eng)
    with eng.begin() as c: assert c.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one()=="6.0.7"

def test_role_landing_is_action_first_and_bounded():
    ws={"role":{"code":"quality"},"command_brief":{"lines":["Q AMBER"]},"action_inbox":{"focused":[{"title":f"A{i}"} for i in range(20)]},"decision_queue":[{"title":f"D{i}"} for i in range(8)],"cockpit":{"domains":{"series":{"band":"AMBER"},"field":{"band":"GREEN"}}}}
    out=build_role_landing(ws); assert out["role"]=="quality"; assert len(out["primary_actions"])==5; assert len(out["decisions"])==3; assert len(out["guided_workflows"])<=3; assert out["progressive_disclosure"]["drilldown_collapsed_by_default"] is True

def test_role_aliases_do_not_change_authorization_semantics():
    assert normalize_role("rd")=="engineering"
    out=build_role_landing({"role":{"code":"rd"},"action_inbox":{"focused":[]},"decision_queue":[],"cockpit":{"domains":{}}}); assert out["governance"]["role_is_ui_focus_not_authorization"] is True and out["governance"]["acl_unchanged"] is True

def test_quality_guides_are_domain_specific():
    out=build_role_landing({"role":{"code":"quality"},"action_inbox":{"focused":[]},"decision_queue":[],"cockpit":{"domains":{}}}); codes={x["code"] for x in out["guided_workflows"]}; assert "defect_investigation" in codes and "suspect_population" in codes

def test_closed_ux_issues_are_not_shown_on_role_landing():
    issues=[{"role":"quality","status":"open","issue_code":"UX-1"},{"role":"quality","status":"closed","issue_code":"UX-2"},{"role":"engineering","status":"open","issue_code":"UX-3"}]
    out=build_role_landing({"role":{"code":"quality"},"action_inbox":{"focused":[]},"decision_queue":[],"cockpit":{"domains":{}}}, issues); assert [x["issue_code"] for x in out["open_usability_issues"]]==["UX-1"]

def test_usability_issue_model_is_aggregate_and_closeable_with_evidence():
    eng=create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng); Session=sessionmaker(bind=eng); db=Session(); db.add(Project(code="P1",name="P1",status="active",phase="development")); db.flush(); pilot=PilotStudy(code="PILOT-1",project_code="P1",name="Pilot",mode="controlled",required_roles=["quality"]); db.add(pilot); db.flush(); row=PilotUsabilityIssue(pilot_id=pilot.id,project_code="P1",issue_code="UX-01",role="quality",surface="project_workspace",category="navigation",severity="medium",title="Too many cards",problem_statement="Engineer needs excessive scrolling",occurrence_count=7,evidence_json={"sessions":12}); db.add(row); db.commit(); db.refresh(row); assert row.occurrence_count==7 and row.status=="open"; row.remediation="Collapse drill-down modules by default"; row.verification_json={"uat_retest":"pass"}; row.status="verified"; row.closed_at=datetime.now(timezone.utc); db.commit(); assert db.get(PilotUsabilityIssue,row.id).status=="verified"


def _pilot_pass_rows(db, pilot):
    from app.db.models import PilotScenarioResult, PilotTelemetryAggregate
    for code, role in [("S1","rd"),("S2","manufacturing"),("S3","quality")]:
        db.add(PilotScenarioResult(pilot_id=pilot.id,scenario_code=code,role=role,required=True,status="pass",baseline_seconds=100,mgc_seconds=50,expected_evidence_count=1,evidence_count=1,usability_rating=4.6))
    db.add(PilotTelemetryAggregate(pilot_id=pilot.id,period_start=datetime.now(timezone.utc),role="quality",surface="workspace",sessions=20,completions=20,errors=0,total_duration_seconds=800))
    pilot.external_gate_evidence_json={k:{"status":"PASS"} for k in ["docker_runtime_acceptance","cve_scan","oidc_negative_tests","backup_restore_drill","performance_pilot"]}
    db.commit()

def test_critical_open_usability_issue_blocks_controlled_go():
    eng=create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng); Session=sessionmaker(bind=eng); db=Session(); db.add(Project(code="P2",name="P2")); db.flush(); pilot=PilotStudy(code="PILOT-2",project_code="P2",name="Pilot",mode="controlled",status="running",required_roles=["rd","manufacturing","quality"]); db.add(pilot); db.flush(); _pilot_pass_rows(db,pilot); db.add(PilotUsabilityIssue(pilot_id=pilot.id,project_code="P2",issue_code="UX-C",role="quality",severity="critical",title="Unsafe workflow ambiguity",problem_statement="Critical action can be misunderstood")); db.commit(); out=evaluate_pilot(db,pilot,reconciliation_report={"pilot_acceptance":{"status":"READY_FOR_CONTROLLED_PILOT"}},security_posture={"status":"PASS"}); assert out["decision"]=="NO_GO"; assert out["usability_issue_closure"]["critical"]==1

def test_verified_usability_issue_no_longer_blocks_go():
    eng=create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng); Session=sessionmaker(bind=eng); db=Session(); db.add(Project(code="P3",name="P3")); db.flush(); pilot=PilotStudy(code="PILOT-3",project_code="P3",name="Pilot",mode="controlled",status="running",required_roles=["rd","manufacturing","quality"]); db.add(pilot); db.flush(); _pilot_pass_rows(db,pilot); db.add(PilotUsabilityIssue(pilot_id=pilot.id,project_code="P3",issue_code="UX-V",role="quality",severity="critical",title="Fixed flow",problem_statement="Was ambiguous",status="verified",remediation="Guided workflow",verification_json={"uat_retest":"pass"})); db.commit(); out=evaluate_pilot(db,pilot,reconciliation_report={"pilot_acceptance":{"status":"READY_FOR_CONTROLLED_PILOT"}},security_posture={"status":"PASS"}); assert out["decision"]=="GO"; assert out["usability_issue_closure"]["critical"]==0
