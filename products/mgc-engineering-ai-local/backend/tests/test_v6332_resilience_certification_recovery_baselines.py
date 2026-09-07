from __future__ import annotations

import hashlib
import json
import pytest

from app.core.resilience_certification import (
    RecoveryRegressionPolicy, attach_integrity, build_baseline, build_campaign,
    certify_recovery, validate_baseline, validate_campaign, validate_certification,
    validate_drill_evidence_for_certification, validate_release_bundle,
)
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def _drill(release='6.3.33', *, api=10.0, worker=12.0, live=True, decision='PASS', profile='core', tier='production'):
    body={
        'schema':'mgc.resilience-drill-evidence.v1','release':release,'database_schema':SCHEMA_VERSION,
        'generated_at':'2026-09-06T00:00:00+00:00','tier':tier,'profile':profile,'plan_sha256':'p',
        'live_execution':live,'decision':decision,
        'results':[
            {'scenario':'api_instance_loss','service':'api','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True,'recovery_seconds':api,'expected_signal_codes':['APPLICATION_HA_UNSAFE'],'notes_code':'TEST','status':'PASS'},
            {'scenario':'worker_cpu_loss','service':'worker-cpu','fault_injected':True,'continuity_passed':True,'recovery_attempted':True,'recovery_passed':True,'recovery_seconds':worker,'expected_signal_codes':['WORKLOAD_RECOVERY_REQUIRED'],'notes_code':'TEST','status':'PASS'},
        ],
        'governance':{'contains_raw_logs':False,'contains_credentials':False,'contains_engineering_document_content':False,'arbitrary_shell_injection_used':False,'automatic_production_authorization':False,'automatic_root_cause_claimed':False,'human_operator_required':True},
    }
    raw=json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    body['integrity']={'algorithm':'sha256','payload_sha256':hashlib.sha256(raw).hexdigest()}
    return body


def _sig(): return {'verified':True,'algorithm':'openssl-sha256','public_key_sha256':'a'*64}


def _baseline(*, bootstrap=False):
    return build_baseline(_drill(),signature_verification=_sig(),approval_reference='CHG-632',approved_at='2026-09-06T01:00:00Z',approved_by_role='release-manager',bootstrap=bootstrap)


def _campaign(base):
    return build_campaign(campaign_id='RC-6334',baseline=base,scenarios=['api_instance_loss','worker_cpu_loss'],profile='core',tier='production',approval_reference='CAB-6334',approved_at='2026-09-06T02:00:00Z',approved_by_role='change-manager')


def test_runtime_contract_6332_no_schema_migration():
    assert APP_VERSION == '6.3.34' and SCHEMA_VERSION == '6.3.13'


def test_previous_release_live_evidence_is_portably_valid():
    assert validate_drill_evidence_for_certification(_drill()) == (True,[])


def test_simulation_cannot_be_promoted_to_baseline():
    with pytest.raises(ValueError,match='invalid drill evidence'):
        build_baseline(_drill(live=False,decision='SIMULATED'),signature_verification=_sig(),approval_reference='X',approved_at='T',approved_by_role='role')


def test_unsigned_evidence_cannot_be_promoted_to_baseline():
    with pytest.raises(ValueError,match='signature'):
        build_baseline(_drill(),signature_verification={'verified':False},approval_reference='X',approved_at='T',approved_by_role='role')


def test_approved_baseline_keeps_per_scenario_and_aggregate_rto():
    b=_baseline(); assert validate_baseline(b)==(True,[])
    assert b['metrics']['per_scenario_rto_seconds']=={'api_instance_loss':10.0,'worker_cpu_loss':12.0}
    assert b['metrics']['aggregate_rto_seconds']==12.0


def test_campaign_requires_baseline_coverage_for_every_scenario():
    b=_baseline()
    with pytest.raises(ValueError,match='baseline has no recovery metric'):
        build_campaign(campaign_id='x',baseline=b,scenarios=['redis_brownout'],profile='core',tier='production',approval_reference='X',approved_at='T',approved_by_role='role')


def test_approved_campaign_is_integrity_bound_to_baseline_and_policy():
    b=_baseline(); c=_campaign(b); assert validate_campaign(c,b)==(True,[])
    assert c['baseline_sha256']==b['integrity']['payload_sha256']
    assert c['policy']['max_rto_ratio']==1.2


def test_recovery_improvement_yields_go_but_not_production_authorization():
    b=_baseline(); c=_campaign(b); current=_drill(APP_VERSION,api=8.0,worker=10.0)
    report=certify_recovery(current_evidence=current,signature_verification=_sig(),baseline=b,campaign=c)
    assert report['decision']=='GO' and report['production_authorized'] is False
    assert validate_certification(report,require_go=True)==(True,[])


def test_ratio_regression_is_automatically_detected_and_blocks_release():
    b=_baseline(); c=_campaign(b); current=_drill(APP_VERSION,api=13.0,worker=10.0)
    report=certify_recovery(current_evidence=current,signature_verification=_sig(),baseline=b,campaign=c)
    assert report['decision']=='NO_GO'
    api=next(x for x in report['scenario_comparisons'] if x['scenario']=='api_instance_loss')
    assert api['status']=='FAIL' and api['ratio']==1.3
    assert 'RTO_REGRESSION_GATE' in report['failed_checks']


def test_absolute_regression_can_block_even_when_ratio_is_within_custom_limit():
    b=_baseline(); c=build_campaign(campaign_id='x',baseline=b,scenarios=['worker_cpu_loss'],profile='core',tier='production',approval_reference='X',approved_at='T',approved_by_role='role',policy=RecoveryRegressionPolicy(max_rto_ratio=2.0,max_absolute_increase_seconds=1.0,rto_ceiling_seconds=120.0))
    report=certify_recovery(current_evidence=_drill(APP_VERSION,api=10,worker=13.5),signature_verification=_sig(),baseline=b,campaign=c)
    assert report['decision']=='NO_GO'


def test_bootstrap_baseline_never_satisfies_previous_release_gate():
    b=_baseline(bootstrap=True); c=_campaign(b)
    report=certify_recovery(current_evidence=_drill(APP_VERSION,api=8,worker=9),signature_verification=_sig(),baseline=b,campaign=c)
    assert report['decision']=='NO_GO' and 'BASELINE_RELEASE_ORDER' in report['failed_checks']


def test_tampered_campaign_or_certification_is_rejected():
    b=_baseline(); c=_campaign(b); c['policy']['max_rto_ratio']=9.0
    ok,errors=validate_campaign(c,b); assert not ok and 'integrity' in errors
    c=_campaign(b); r=certify_recovery(current_evidence=_drill(APP_VERSION,api=8,worker=9),signature_verification=_sig(),baseline=b,campaign=c)
    r['decision']='NO_GO'; ok,errors=validate_certification(r); assert not ok and 'integrity' in errors


def test_non_adjacent_baseline_is_rejected_by_release_order_gate():
    old = build_baseline(_drill('6.3.32'), signature_verification=_sig(), approval_reference='CHG-630', approved_at='2026-09-05T01:00:00Z', approved_by_role='release-manager')
    campaign = _campaign(old)
    report = certify_recovery(current_evidence=_drill(APP_VERSION, api=8, worker=9), signature_verification=_sig(), baseline=old, campaign=campaign)
    assert report['decision'] == 'NO_GO'
    assert 'BASELINE_RELEASE_ORDER' in report['failed_checks']


def test_profile_or_tier_mismatch_blocks_certification():
    b = _baseline(); c = _campaign(b)
    report = certify_recovery(current_evidence=_drill(APP_VERSION, api=8, worker=9, tier='staging'), signature_verification=_sig(), baseline=b, campaign=c)
    assert report['decision'] == 'NO_GO'
    assert 'PROFILE_TIER_MATCH' in report['failed_checks']


def test_semantically_forged_baseline_is_rejected_even_with_recomputed_integrity():
    b = _baseline()
    b['metrics']['aggregate_rto_seconds'] = 1.0
    b = attach_integrity(b)
    ok, errors = validate_baseline(b)
    assert not ok and 'aggregate_rto_seconds' in errors


def test_standalone_go_rewrite_cannot_pass_source_bundle_recomputation():
    b = _baseline(); c = _campaign(b); current = _drill(APP_VERSION, api=8, worker=9)
    report = certify_recovery(current_evidence=current, signature_verification=_sig(), baseline=b, campaign=c)
    forged = dict(report)
    forged['campaign_id'] = 'FORGED-CAMPAIGN'
    forged = attach_integrity(forged)
    ok, errors = validate_release_bundle(forged, current_evidence=current, signature_verification=_sig(), baseline=b, campaign=c, require_go=True)
    assert not ok and 'certification_recompute_mismatch' in errors
