from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401
from app.db.migrations import ensure_v606_schema
from app.db.models import PilotScenarioResult, PilotStudy, PilotTelemetryAggregate, Project
from app.db.session import Base
from app.services.pilot_acceptance import evaluate_pilot, sanitize_telemetry_metadata


def db_session():
    engine=create_engine('sqlite:///:memory:'); Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine); db=Session()
    db.add(Project(code='P1',name='Pilot Vehicle')); db.commit()
    return engine, db


def _pilot(db, mode='controlled'):
    p=PilotStudy(code='PILOT-1',project_code='P1',name='Controlled Pilot',mode=mode,status='running',required_roles=['rd','manufacturing','quality'],external_gate_evidence_json={})
    db.add(p); db.commit(); db.refresh(p); return p


def _good_rows(db,p):
    for code,role in [('S1','rd'),('S2','manufacturing'),('S3','quality')]:
        db.add(PilotScenarioResult(pilot_id=p.id,scenario_code=code,role=role,domain='engineering',required=True,status='pass',baseline_seconds=100,mgc_seconds=50,expected_evidence_count=2,evidence_count=2,usability_rating=4.5))
    db.add(PilotTelemetryAggregate(pilot_id=p.id,period_start=datetime.now(timezone.utc),role='rd',surface='cockpit',sessions=100,completions=99,errors=1,total_duration_seconds=5000,metadata_json={'client':'pilot'}))
    db.commit()


def _external_pass(p):
    p.external_gate_evidence_json={k:{'status':'PASS','evidence_ref':'corporate-run'} for k in ['docker_runtime_acceptance','cve_scan','oidc_negative_tests','backup_restore_drill','performance_pilot']}


def test_v606_schema_marker_is_additive_and_idempotent():
    engine=create_engine('sqlite:///:memory:'); Base.metadata.create_all(engine)
    ensure_v606_schema(engine); ensure_v606_schema(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT schema_version FROM mgc_schema_state WHERE id=1')).scalar_one() == '6.0.6'


def test_synthetic_pilot_can_never_authorize_go():
    _,db=db_session(); p=_pilot(db,'synthetic'); _good_rows(db,p)
    out=evaluate_pilot(db,p,reconciliation_report={'pilot_acceptance':{'status':'READY_FOR_CONTROLLED_PILOT'}},security_posture={'status':'PASS'})
    assert out['decision']=='PRECHECK_PASS'
    assert out['governance']['synthetic_data_can_authorize_go'] is False


def test_controlled_pilot_go_requires_all_critical_gates():
    _,db=db_session(); p=_pilot(db); _good_rows(db,p); _external_pass(p); db.commit()
    out=evaluate_pilot(db,p,reconciliation_report={'pilot_acceptance':{'status':'READY_FOR_CONTROLLED_PILOT'}},security_posture={'status':'PASS'})
    assert out['decision']=='GO' and not out['blockers']
    assert out['human_go_live_required'] is True


def test_missing_external_gate_forces_no_go():
    _,db=db_session(); p=_pilot(db); _good_rows(db,p); _external_pass(p); p.external_gate_evidence_json.pop('cve_scan'); db.commit()
    out=evaluate_pilot(db,p,reconciliation_report={'pilot_acceptance':{'status':'READY_FOR_CONTROLLED_PILOT'}},security_posture={'status':'PASS'})
    assert out['decision']=='NO_GO'
    assert any(x['code']=='external:cve_scan' for x in out['blockers'])


def test_usability_or_time_target_can_only_yield_conditional_go():
    _,db=db_session(); p=_pilot(db); _good_rows(db,p); _external_pass(p)
    rows=db.query(PilotScenarioResult).all()
    for x in rows: x.mgc_seconds=90; x.usability_rating=3.8
    db.commit()
    out=evaluate_pilot(db,p,reconciliation_report={'pilot_acceptance':{'status':'READY_FOR_CONTROLLED_PILOT'}},security_posture={'status':'PASS'})
    assert out['decision']=='CONDITIONAL_GO'
    assert all(x['severity']=='warning' for x in out['blockers'])


def test_required_role_missing_is_no_go():
    _,db=db_session(); p=_pilot(db); _external_pass(p)
    for code,role in [('S1','rd'),('S2','manufacturing')]:
        db.add(PilotScenarioResult(pilot_id=p.id,scenario_code=code,role=role,required=True,status='pass',baseline_seconds=100,mgc_seconds=40,expected_evidence_count=1,evidence_count=1,usability_rating=5))
    db.commit()
    out=evaluate_pilot(db,p,reconciliation_report={'pilot_acceptance':{'status':'READY_FOR_CONTROLLED_PILOT'}},security_posture={'status':'PASS'})
    assert out['decision']=='NO_GO'
    assert any(x['code']=='required_role_coverage' for x in out['blockers'])


def test_telemetry_rejects_employee_or_content_identifiers():
    for key in ['user','email','ip_address','query_text','vin','document_id']:
        with pytest.raises(ValueError): sanitize_telemetry_metadata({key:'secret'})
    assert sanitize_telemetry_metadata({'client':'web','build':'pilot'})=={'client':'web','build':'pilot'}


def test_golden_dataset_is_synthetic_deterministic_and_has_no_real_people():
    root=Path(__file__).resolve().parents[2]
    data=json.loads((root/'pilot/golden_dataset_v1.json').read_text())
    assert data['schema']=='mgc-golden-automotive-dataset-v1'
    assert data['synthetic_only'] is True and data['authorizes_production_go'] is False
    assert data['privacy']=={'real_people':False,'real_vins':False,'customer_data':False,'employee_tracking':False}
    assert data['counts']=={'parts':60,'bom_edges':59,'vehicles':24,'defects':3}
