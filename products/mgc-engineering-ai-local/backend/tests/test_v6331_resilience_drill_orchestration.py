from __future__ import annotations
import json
import pytest
from app.core.resilience_drill import bind_incident_evidence, build_evidence, build_plan, catalog, validate_evidence, validate_plan
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def test_runtime_contract_6331_no_schema_migration():
    assert APP_VERSION == '6.3.34' and SCHEMA_VERSION == '6.3.13'


def test_catalog_is_bounded_and_has_no_arbitrary_shell():
    c=catalog(); assert len(c['scenarios'])==5
    assert c['governance']['arbitrary_shell_injection_allowed'] is False
    assert c['governance']['production_authorized'] is False


def test_staging_dependency_drill_plan_is_valid():
    p=build_plan(['redis_brownout','qdrant_brownout'],tier='staging',profile='ai')
    assert validate_plan(p)==(True,[])


def test_production_dependency_drill_fails_closed_without_override_and_window():
    with pytest.raises(ValueError, match='override'):
        build_plan(['redis_brownout'],tier='production',profile='core')
    with pytest.raises(ValueError, match='maintenance_window_ref'):
        build_plan(['redis_brownout'],tier='production',profile='core',allow_production_dependency_drill=True)


def test_production_api_and_worker_drills_are_bounded_by_default():
    p=build_plan(['api_instance_loss','worker_cpu_loss'],tier='production',profile='core')
    assert validate_plan(p)==(True,[])
    assert {x['blast_radius'] for x in p['scenarios']}=={'single_api_replica','single_cpu_worker'}


def test_qdrant_rejected_for_core_profile():
    with pytest.raises(ValueError, match='not valid for profile core'):
        build_plan(['qdrant_brownout'],profile='core')


def test_live_evidence_requires_fault_continuity_and_recovery():
    p=build_plan(['api_instance_loss'])
    good=build_evidence(p,[{'scenario':'api_instance_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True,'recovery_seconds':2.1}],live_execution=True)
    assert good['decision']=='PASS' and validate_evidence(good)==(True,[])
    bad=build_evidence(p,[{'scenario':'api_instance_loss','fault_injected':True,'continuity_passed':False,'recovery_attempted':True,'recovery_passed':True}],live_execution=True)
    assert bad['decision']=='FAIL'


def test_simulation_cannot_become_pass_evidence():
    p=build_plan(['api_instance_loss'])
    report=build_evidence(p,[{'scenario':'api_instance_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True}],live_execution=False)
    assert report['decision']=='SIMULATED'
    assert report['governance']['automatic_production_authorization'] is False


def test_tamper_is_detected():
    p=build_plan(['api_instance_loss'])
    report=build_evidence(p,[{'scenario':'api_instance_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True}],live_execution=True)
    tampered=json.loads(json.dumps(report)); tampered['decision']='FAIL'
    valid,errors=validate_evidence(tampered)
    assert not valid and 'integrity' in errors


def test_incident_binding_copies_only_hash_and_codes():
    import hashlib
    p=build_plan(['api_instance_loss'])
    report=build_evidence(p,[{'scenario':'api_instance_loss','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True}],live_execution=True)
    incident={"schema":"mgc.production-incident-evidence.v1","release":APP_VERSION,"database_schema":SCHEMA_VERSION,"generated_at":"2026-09-06T00:00:00+00:00","status":"INCIDENT_SIGNALS","signal_count":1,"highest_severity":"critical","severity_counts":{"low":0,"medium":0,"high":0,"critical":1},"signals":[{"code":"APPLICATION_HA_UNSAFE","severity":"critical","component":"application-ha","summary":"secret-looking narrative","signal_fingerprint":"x","evidence":{"raw":"DO-NOT-COPY"}}],"governance":{"contains_raw_logs":False,"contains_document_content":False,"contains_queries":False,"contains_credentials":False,"bounded_cardinality":True,"automatic_destructive_recovery":False,"automatic_incident_resolution":False,"production_authorized":False,"human_operator_required":True}}
    raw=json.dumps(incident,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode(); incident['integrity']={"algorithm":"sha256","payload_sha256":hashlib.sha256(raw).hexdigest()}
    bound=bind_incident_evidence(report,incident)
    blob=json.dumps(bound)
    assert bound['incident_evidence_binding']['correlation_status']=='OBSERVED'
    assert 'DO-NOT-COPY' not in blob and 'secret-looking narrative' not in blob
    assert validate_evidence(bound)==(True,[])
