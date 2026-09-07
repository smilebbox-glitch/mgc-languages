from types import SimpleNamespace

import app.core.cutover_safety as cut
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def settings(**kw):
    base=dict(cutover_max_patch_rollback_skew=1, blue_green_enabled=True,
              cutover_candidate_min_ready_samples=3, cutover_post_switch_samples=5,
              cutover_failure_threshold=2)
    base.update(kw); return SimpleNamespace(**base)


def test_release_marker():
    assert APP_VERSION == '6.3.34' and SCHEMA_VERSION == '6.3.13'


def test_rollback_one_patch_same_schema(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    r=cut.rollback_compatibility('6.3.33','6.3.13')
    assert r.compatible and r.reason == 'compatible'


def test_rollback_schema_change_fails_closed(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    r=cut.rollback_compatibility('6.3.30','6.3.12')
    assert not r.compatible and r.reason == 'schema_rollback_forbidden'


def test_rollback_two_patches_fails_closed(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    r=cut.rollback_compatibility('6.3.29','6.3.13')
    assert not r.compatible and r.reason == 'rollback_patch_skew_exceeded'


def test_rollback_to_newer_fails_closed(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    r=cut.rollback_compatibility('6.3.35','6.3.13')
    assert not r.compatible and r.reason == 'target_is_newer_than_current'


def test_cutover_snapshot_candidate_and_stable(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    monkeypatch.setattr(cut, 'deployment_safety_snapshot', lambda touch_api=False: {
        'registry_status':'available','incompatible_components':0,
        'components':[
            {'component':'api','node':'api@stable','deployment_slot':'stable','app_version':'6.3.33','schema_version':'6.3.13','compatibility':{'compatible':True}},
            {'component':'api','node':'api@candidate','deployment_slot':'candidate','app_version':'6.3.34','schema_version':'6.3.13','compatibility':{'compatible':True}},
        ]})
    s=cut.cutover_safety_snapshot()
    assert s['candidate_visible'] is True
    assert s['candidate_runtime_compatible'] is True
    assert s['automatic_rollback_safe'] is True
    assert s['cutover_preconditions_met'] is True


def test_cutover_snapshot_missing_candidate_blocks_when_registry_available(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    monkeypatch.setattr(cut, 'deployment_safety_snapshot', lambda touch_api=False: {'registry_status':'available','incompatible_components':0,'components':[]})
    s=cut.cutover_safety_snapshot()
    assert s['candidate_visible'] is False and s['cutover_preconditions_met'] is False


def test_cutover_snapshot_incompatible_candidate_blocks(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    monkeypatch.setattr(cut, 'deployment_safety_snapshot', lambda touch_api=False: {
        'registry_status':'available','incompatible_components':1,
        'components':[{'component':'api','node':'bad','deployment_slot':'candidate','app_version':'6.3.10','schema_version':'6.3.13','compatibility':{'compatible':False}}]})
    s=cut.cutover_safety_snapshot()
    assert not s['candidate_runtime_compatible'] and not s['cutover_preconditions_met']


def test_registry_outage_does_not_claim_candidate_visibility(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    monkeypatch.setattr(cut, 'deployment_safety_snapshot', lambda touch_api=False: {'registry_status':'unavailable','incompatible_components':0,'components':[]})
    s=cut.cutover_safety_snapshot()
    assert not s['candidate_visible']
    assert s['policy']['registry_is_diagnostic_not_authoritative'] is True


def test_policy_never_authorizes_production(monkeypatch):
    monkeypatch.setattr(cut, 'get_settings', lambda: settings())
    monkeypatch.setattr(cut, 'deployment_safety_snapshot', lambda touch_api=False: {'registry_status':'unavailable','incompatible_components':0,'components':[]})
    assert cut.cutover_safety_snapshot()['policy']['production_authorized'] is False
