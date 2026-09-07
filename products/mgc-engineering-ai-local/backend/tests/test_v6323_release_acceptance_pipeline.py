from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.core import load_certification as lc
from app.core import production_certification as pc
from app.core import release_acceptance as ra
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def topology(profile='15'):
    return {'schema':'mgc-multihost-topology-v1','profile':profile,'nodes':[{'node_id':'a','failure_domain':'fd-a','roles':['api']},{'node_id':'b','failure_domain':'fd-b','roles':['api']} ]}


def source_evidence(profile='15'):
    p=pc.PROFILES[profile]
    return {'schema':pc.EVIDENCE_SCHEMA,'named_users':p.named_users,'http':{},'dependencies':{'availability':1.0},'database_pool':{},'external_load_balancer':{'successful_probes':30,'non_idempotent_replay_detected':False},'failover':{'host_loss_passed':True,'authoritative_failover_passed':True,'evidence_integrity_passed':True,'rto_seconds':p.rto_seconds*0.8,'rpo_seconds':p.rpo_seconds*0.8}}


def load(profile='15', *, p95=100.0, p99=130.0, rps=100.0, err=0.001, pool=.5):
    p=lc.LOAD_PROFILES[profile]
    operations={op:{'requests':max(1,p.min_requests//len(lc.REQUIRED_WORKLOAD_OPERATIONS))} for op in lc.REQUIRED_WORKLOAD_OPERATIONS}
    ev={'schema':lc.LOAD_EVIDENCE_SCHEMA,'release':APP_VERSION,'schema_version':SCHEMA_VERSION,'profile':profile,'named_users':p.named_users,'concurrency':p.concurrency,'workload':lc.workload_contract(),'summary':{'requests':p.min_requests,'p50_ms':80.0,'p95_ms':p95,'p99_ms':p99,'max_ms':p99+20,'error_rate':err,'requests_per_second':rps,'error_budget':{'consumed_ratio':min(1.0,err/max(p.error_rate_max,1e-9))},'operations':operations},'saturation':{'db_pool':{'max_saturation_ratio':pool},'queue':{'max_oldest_job_age_seconds':1.0},'workload':{'max_dead_letter_jobs':0,'max_orphaned_jobs':0,'max_expired_running_leases':0}},'governance':{'live_target_measurement':True,'synthetic':False,'engineering_state_mutation_allowed':False,'non_idempotent_business_write_replay_allowed':False}}
    return lc.attach_integrity(ev,detached_signature_verified=True,signature_algorithm='test')


def technical(profile='15', load_ev=None):
    ev=source_evidence(profile); ev['load_certification']=load_ev or load(profile); s=ev['load_certification']['summary']; ev['http']={'requests':s['requests'],'p95_ms':s['p95_ms'],'error_rate':s['error_rate']}; ev['database_pool']={'max_saturation_ratio':ev['load_certification']['saturation']['db_pool']['max_saturation_ratio']}
    return pc.evaluate_target_host_evidence(profile=profile,topology=topology(profile),evidence=ev)


def approved_baseline(profile='15', **metrics):
    base={'p95_ms':100.0,'p99_ms':130.0,'error_rate':0.001,'requests_per_second':100.0,'db_pool_max_saturation_ratio':.5,'rto_seconds':240.0,'rpo_seconds':240.0}; base.update(metrics)
    b={'schema':ra.APPROVED_BASELINE_SCHEMA,'release':'6.3.23','schema_version':SCHEMA_VERSION,'profile':profile,'technical_decision':'GO','human_approved':True,'bootstrap':False,'approval':{'reference':'CHG-123','approved_at':'2026-09-05T00:00:00Z'},'metrics':base,'source_acceptance_sha256':'a'*64,'source_chain_sequence':1,'source_parent_acceptance_sha256':None,'governance':{'promoted_from_signed_acceptance':True}}
    b=ra.attach_integrity(b,detached_signature_verified=True,signature_algorithm='test'); return b


def test_release_marker():
    assert APP_VERSION=='6.3.34' and SCHEMA_VERSION=='6.3.13'


def test_no_baseline_is_conditional_not_go():
    le=load(); r=ra.build_release_acceptance(profile='15',production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence(),baseline=None)
    assert r['decision']=='CONDITIONAL' and r['baseline_regression']['missing_checks']==['APPROVED_BASELINE']


def test_good_approved_baseline_allows_release_go_but_not_authorization():
    le=load(); r=ra.build_release_acceptance(profile='15',production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence(),baseline=approved_baseline())
    assert r['decision']=='GO' and r['production_authorized'] is False and r['human_approval_required'] is True
    assert r['chain']['sequence']==2 and r['chain']['parent_acceptance_sha256']=='a'*64

@pytest.mark.parametrize('metric,value,code',[
    ('p95_ms',116.0,'REGRESSION_P95'),('p99_ms',157.0,'REGRESSION_P99'),('requests_per_second',89.0,'REGRESSION_THROUGHPUT'),('db_pool_max_saturation_ratio',.61,'REGRESSION_DB_POOL'),('rto_seconds',289.0,'REGRESSION_RTO'),('rpo_seconds',289.0,'REGRESSION_RPO')])
def test_regression_thresholds_fail_closed(metric,value,code):
    le=load(); current=ra.extract_metrics(production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence()); current[metric]=value
    r=ra.evaluate_regression(current_metrics=current,baseline=approved_baseline(),profile='15')
    assert r['decision']=='NO_GO' and code in r['failed_checks']


def test_error_rate_absolute_regression_is_no_go():
    le=load(); cur=ra.extract_metrics(production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence()); cur['error_rate']=.0031
    r=ra.evaluate_regression(current_metrics=cur,baseline=approved_baseline(),profile='15')
    assert 'REGRESSION_ERROR_RATE' in r['failed_checks']


def test_unapproved_or_wrong_profile_baseline_fails():
    le=load(); cur=ra.extract_metrics(production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence())
    b=approved_baseline(); b['human_approved']=False; b=ra.attach_integrity(b,detached_signature_verified=True)
    assert 'BASELINE_HUMAN_APPROVED' in ra.evaluate_regression(current_metrics=cur,baseline=b,profile='15')['failed_checks']
    b=approved_baseline(); b['profile']='30'; b=ra.attach_integrity(b,detached_signature_verified=True)
    assert 'BASELINE_PROFILE' in ra.evaluate_regression(current_metrics=cur,baseline=b,profile='15')['failed_checks']


def test_baseline_must_be_older_same_release_line():
    le=load(); cur=ra.extract_metrics(production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence())
    b=approved_baseline(); b['release']='6.3.34'; b=ra.attach_integrity(b,detached_signature_verified=True)
    assert 'BASELINE_RELEASE_ORDER' in ra.evaluate_regression(current_metrics=cur,baseline=b,profile='15')['failed_checks']


def test_bootstrap_promotion_only_allows_missing_baseline_conditional():
    le=load(); a=ra.build_release_acceptance(profile='15',production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence(),baseline=None)
    a['integrity']['detached_signature_verified']=True
    b=ra.baseline_from_acceptance(acceptance=a,approval_reference='CHG-BOOT',approved_at='2026-09-06T00:00:00Z',bootstrap=True)
    assert b['bootstrap'] is True and b['human_approved'] is True
    with pytest.raises(ValueError): ra.baseline_from_acceptance(acceptance=a,approval_reference='CHG-X',approved_at='x',bootstrap=False)


def test_tampered_baseline_digest_fails_closed():
    le=load(); cur=ra.extract_metrics(production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence())
    b=approved_baseline(); b['metrics']['p95_ms']=999
    assert 'BASELINE_DIGEST' in ra.evaluate_regression(current_metrics=cur,baseline=b,profile='15')['failed_checks']


def test_source_contracts_include_explicit_disruptive_confirmation_and_chain_verifier():
    root=Path(__file__).resolve().parents[2]
    wrapper=(root/'scripts/automated_release_acceptance.sh').read_text()
    chain=(root/'scripts/verify_acceptance_chain.py').read_text()
    assert 'MGC_RELEASE_ACCEPTANCE_DISRUPTIVE_CONFIRM' in wrapper
    assert "reasons.append('parent')" in chain

def test_same_release_baseline_is_only_allowed_for_sequence_one_bootstrap():
    le=load(); cur=ra.extract_metrics(production_report=technical(load_ev=le),load_evidence=le,source_evidence=source_evidence())
    b=approved_baseline(); b['release']=APP_VERSION; b['bootstrap']=True; b['source_chain_sequence']=1; b=ra.attach_integrity(b,detached_signature_verified=True)
    assert 'BASELINE_RELEASE_ORDER' not in ra.evaluate_regression(current_metrics=cur,baseline=b,profile='15')['failed_checks']
    b['bootstrap']=False; b=ra.attach_integrity(b,detached_signature_verified=True)
    assert 'BASELINE_RELEASE_ORDER' in ra.evaluate_regression(current_metrics=cur,baseline=b,profile='15')['failed_checks']
