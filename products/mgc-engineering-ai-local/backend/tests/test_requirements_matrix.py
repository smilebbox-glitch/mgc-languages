from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    Document, DocumentStatus, EngineeringRequirement, LaunchTrial, Project, RequirementVerification,
)
from app.db.session import Base
from app.services.project_workspace import project_workspace
from app.services.requirements_matrix import requirements_matrix


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _project(db: Session, code='REQ1', area='assembly'):
    p=Project(code=code,name='Requirements project',acl_groups=['engineering-ai-users'])
    d=Document(filename='oem-spec.pdf',stored_path='/tmp/spec',sha256='a'*64,status=DocumentStatus.ready,
               part_number='P1',revision='A',doc_type='requirement',project_code=code,manufacturing_area=area,
               acl_groups=['engineering-ai-users'])
    db.add_all([p,d]); db.commit(); db.refresh(d)
    return p,d


def test_critical_requirement_without_verification_is_blocker():
    db=_db(); p,d=_project(db)
    db.add(EngineeringRequirement(project_code=p.code,manufacturing_area='assembly',code='OEM-001',category='oem',criticality='critical',
        title='Noise limit',requirement_text='Vehicle noise shall remain below target',source_document_id=d.id,part_numbers=['P1'],status='active'))
    db.commit()
    out=requirements_matrix(db,p.code,{d.id},{'P1'},'assembly',{'assembly'})
    assert out['configured'] is True
    assert out['gates']['source']==100.0
    assert any(x['type']=='verification_missing' and x['severity']=='critical' for x in out['gaps'])
    assert out['status']=='blocked'


def test_passed_verification_requires_visible_proof_to_count():
    db=_db(); p,d=_project(db,code='REQ2')
    r=EngineeringRequirement(project_code=p.code,manufacturing_area='assembly',code='REQ-2',category='system',criticality='important',
        title='Interface',requirement_text='Interface shall meet target',source_document_id=d.id,part_numbers=['P1'],status='active')
    db.add(r); db.commit(); db.refresh(r)
    db.add(RequirementVerification(project_code=p.code,requirement_id=r.id,manufacturing_area='assembly',code='V-2',verification_type='test',phase='dv',
        title='DV test',status='passed',result_summary='Passed',requirement_updated_at_snapshot=r.updated_at,source_document_sha256_snapshot=d.sha256))
    db.commit()
    out=requirements_matrix(db,p.code,{d.id},{'P1'},'assembly',{'assembly'})
    row=out['requirements'][0]
    assert row['verifications'][0]['effective_pass'] is False
    assert any(x['type']=='verification_evidence' for x in out['gaps'])


def test_verification_becomes_stale_after_requirement_changes():
    db=_db(); p,d=_project(db,code='REQ3')
    r=EngineeringRequirement(project_code=p.code,manufacturing_area='assembly',code='REQ-3',category='oem',criticality='critical',
        title='Torque',requirement_text='Torque shall be 120 Nm',source_document_id=d.id,part_numbers=['P1'],status='active')
    db.add(r); db.commit(); db.refresh(r)
    v=RequirementVerification(project_code=p.code,requirement_id=r.id,manufacturing_area='assembly',code='V-3',verification_type='measurement',phase='pv',
        title='Torque audit',status='passed',result_summary='120 Nm confirmed',evidence_document_ids=[d.id],requirement_updated_at_snapshot=r.updated_at,
        source_document_sha256_snapshot=d.sha256,evidence_snapshot_json={d.id:d.sha256})
    db.add(v); db.commit()
    first=requirements_matrix(db,p.code,{d.id},{'P1'},'assembly',{'assembly'})
    assert first['requirements'][0]['verifications'][0]['effective_pass'] is True
    r.requirement_text='Torque shall be 125 Nm'; db.commit(); db.refresh(r)
    second=requirements_matrix(db,p.code,{d.id},{'P1'},'assembly',{'assembly'})
    assert second['requirements'][0]['verifications'][0]['stale'] is True
    assert any(x['type']=='verification_stale' for x in second['gaps'])


def test_passed_launch_trial_can_be_verification_evidence():
    db=_db(); p,d=_project(db,code='REQ4')
    r=EngineeringRequirement(project_code=p.code,manufacturing_area='assembly',code='REQ-4',category='manufacturing',criticality='important',
        title='Capacity',requirement_text='Line shall achieve 60 units/hour',source_document_id=d.id,part_numbers=['P1'],status='active')
    db.add(r); db.commit(); db.refresh(r)
    t=LaunchTrial(project_code=p.code,manufacturing_area='assembly',part_number='P1',code='RAR-REQ4',trial_type='run_at_rate',title='Run at Rate',status='passed',target_rate_per_hour=60,actual_rate_per_hour=61)
    db.add(t); db.commit(); db.refresh(t)
    db.add(RequirementVerification(project_code=p.code,requirement_id=r.id,manufacturing_area='assembly',code='V-4',verification_type='test',phase='pre_launch',
        title='Run at Rate confirmation',status='passed',result_summary='61 units/hour',launch_trial_id=t.id,requirement_updated_at_snapshot=r.updated_at,source_document_sha256_snapshot=d.sha256))
    db.commit()
    out=requirements_matrix(db,p.code,{d.id},{'P1'},'assembly',{'assembly'})
    assert out['requirements'][0]['verifications'][0]['effective_pass'] is True
    assert out['gates']['verification_result']==100.0


def test_requirements_respect_area_and_document_acl():
    db=_db(); p,d=_project(db,code='REQ5',area='assembly')
    hidden=Document(filename='paint-secret.pdf',stored_path='/tmp/paint',sha256='b'*64,status=DocumentStatus.ready,part_number='P2',revision='A',doc_type='requirement',project_code=p.code,manufacturing_area='paint',acl_groups=['paint-secret'])
    db.add(hidden); db.commit(); db.refresh(hidden)
    db.add_all([
        EngineeringRequirement(project_code=p.code,manufacturing_area='assembly',code='ASM-REQ',title='Assembly req',requirement_text='Assembly requirement',source_document_id=d.id,part_numbers=['P1']),
        EngineeringRequirement(project_code=p.code,manufacturing_area='paint',code='PAINT-REQ',title='Paint req',requirement_text='Secret paint requirement',source_document_id=hidden.id,part_numbers=['P2']),
    ]); db.commit()
    out=requirements_matrix(db,p.code,{d.id},{'P1'},None,{'assembly'})
    assert {x['code'] for x in out['requirements']}=={'ASM-REQ'}


def test_project_workspace_adds_requirements_gate_only_when_configured():
    db=_db(); p,d=_project(db,code='REQ6')
    first=project_workspace(db,p,{d.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    assert first['readiness']['gates']['requirements'] is None
    db.add(EngineeringRequirement(project_code=p.code,manufacturing_area='assembly',code='REQ-6',category='oem',criticality='important',title='Requirement',requirement_text='Must be verified',source_document_id=d.id,part_numbers=['P1']))
    db.commit()
    second=project_workspace(db,p,{d.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    assert second['readiness']['gates']['requirements'] is not None
    assert second['requirements_matrix']['configured'] is True
    assert any(x['type']=='requirement' for x in second['readiness']['blockers'])
