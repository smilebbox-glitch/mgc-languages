from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    Document, DocumentStatus, IncomingQualityRecord, LaunchTrial, LocalizationItem,
    PPAPSubmission, Problem8D, Project,
)
from app.db.session import Base
from app.services.project_workspace import project_workspace
from app.services.supplier_localization import create_localization_evidence_pack, supplier_localization_workspace


def _db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _project(db: Session, code='LOC1'):
    p = Project(code=code, name='Localization project', acl_groups=['engineering-ai-users'])
    d = Document(filename='part.pdf', stored_path='/tmp/part', sha256='a'*64, status=DocumentStatus.ready,
                 part_number='P1', revision='A', doc_type='drawing', project_code=code, manufacturing_area='components',
                 acl_groups=['engineering-ai-users'])
    cad = Document(filename='part.step', stored_path='/tmp/part.step', sha256='b'*64, status=DocumentStatus.ready,
                   part_number='P1', revision='A', doc_type='cad', project_code=code, manufacturing_area='components',
                   acl_groups=['engineering-ai-users'])
    db.add_all([p,d,cad]); db.commit(); db.refresh(d); db.refresh(cad)
    return p,d,cad


def test_localization_percent_is_not_supplier_readiness():
    db=_db(); p,d,_=_project(db)
    db.add(LocalizationItem(project_code=p.code, manufacturing_area='components', part_number='P1', supplier_code='SUP1', supplier_name='Local Supplier',
                            localization_percent=100, target_localization_percent=90, status='approved', technical_package_status='missing',
                            rfq_status='complete', nomination_status='approved', tooling_status='ready', capacity_status='confirmed'))
    db.commit()
    out=supplier_localization_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    assert out['localization_kpi']==100.0
    assert out['localization_kpi_is_readiness'] is False
    assert out['score'] < 100
    assert any(x['type']=='technical_package' and x['severity']=='critical' for x in out['gaps'])


def test_release_stage_requires_ppap_and_capacity_evidence():
    db=_db(); p,d,_=_project(db, 'LOC2')
    db.add(LocalizationItem(project_code=p.code, manufacturing_area='components', part_number='P1', supplier_code='SUP1', supplier_name='Supplier',
                            status='sop', technical_package_status='ready', rfq_status='complete', nomination_status='approved', tooling_status='ready', capacity_status='planned'))
    db.commit()
    out=supplier_localization_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    assert any(x['type']=='capacity' and x['severity']=='critical' for x in out['gaps'])
    assert any(x['type']=='ppap' and x['severity']=='critical' for x in out['gaps'])
    assert out['status']=='blocked'


def test_run_at_rate_and_approved_ppap_confirm_supplier_readiness():
    db=_db(); p,d,_=_project(db, 'LOC3')
    db.add(LocalizationItem(project_code=p.code, manufacturing_area='components', part_number='P1', supplier_code='SUP1', supplier_name='Supplier',
                            status='approved', technical_package_status='ready', rfq_status='complete', nomination_status='approved', tooling_status='ready', capacity_status='in_progress'))
    db.add(PPAPSubmission(project_code=p.code, manufacturing_area='components', part_number='P1', supplier_code='SUP1', supplier_name='Supplier', status='approved'))
    db.add(LaunchTrial(project_code=p.code, manufacturing_area='components', part_number='P1', code='RAR-LOC3', trial_type='run_at_rate', title='Supplier Run@Rate',
                       status='passed', target_rate_per_hour=60, actual_rate_per_hour=64))
    db.commit()
    out=supplier_localization_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    assert out['gates']['ppap']==100.0
    assert out['gates']['capacity']==100.0
    assert not any(x['type'] in {'ppap','capacity'} for x in out['gaps'])


def test_incoming_quality_over_limit_is_critical_and_requires_8d():
    db=_db(); p,d,_=_project(db, 'LOC4')
    db.add(LocalizationItem(project_code=p.code, manufacturing_area='components', part_number='P1', supplier_code='SUP1', supplier_name='Supplier', status='validation',
                            technical_package_status='ready', rfq_status='complete', nomination_status='approved', tooling_status='ready', capacity_status='confirmed'))
    db.add(IncomingQualityRecord(project_code=p.code, manufacturing_area='components', code='IQ-1', supplier_code='SUP1', supplier_name='Supplier', part_number='P1',
                                 inspected_quantity=100, rejected_quantity=5, defect_quantity=5, severity='critical', status='open', acceptance_limit_pct=1.0))
    db.commit()
    out=supplier_localization_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    assert any(x['type']=='incoming_quality_limit' and x['severity']=='critical' for x in out['gaps'])
    assert any(x['type']=='supplier_8d_missing' and x['severity']=='critical' for x in out['gaps'])
    assert out['gates']['incoming_quality'] < 100


def test_linked_8d_is_reflected_in_risk_closure():
    db=_db(); p,d,_=_project(db, 'LOC5')
    problem=Problem8D(project_code=p.code, manufacturing_area='components', part_number='P1', title='Supplier defect', severity='high', status='corrective_action')
    db.add(problem); db.commit(); db.refresh(problem)
    db.add(LocalizationItem(project_code=p.code, manufacturing_area='components', part_number='P1', supplier_code='SUP1', supplier_name='Supplier'))
    db.add(IncomingQualityRecord(project_code=p.code, manufacturing_area='components', code='IQ-5', supplier_code='SUP1', part_number='P1', inspected_quantity=10, defect_quantity=1,
                                 severity='high', status='investigating', linked_8d_id=problem.id))
    db.commit()
    out=supplier_localization_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    assert not any(x['type']=='supplier_8d_missing' for x in out['gaps'])
    assert out['gates']['risk_closure'] < 100


def test_localization_respects_area_and_visible_parts():
    db=_db(); p,d,_=_project(db, 'LOC6')
    hidden=Document(filename='paint.pdf',stored_path='/tmp/paint',sha256='c'*64,status=DocumentStatus.ready,part_number='P2',revision='A',doc_type='drawing',project_code=p.code,manufacturing_area='paint',acl_groups=['paint-secret'])
    db.add(hidden)
    db.add_all([
        LocalizationItem(project_code=p.code,manufacturing_area='components',part_number='P1',supplier_code='SUP1',supplier_name='Visible'),
        LocalizationItem(project_code=p.code,manufacturing_area='paint',part_number='P2',supplier_code='SUP2',supplier_name='Hidden'),
    ]); db.commit()
    out=supplier_localization_workspace(db,p.code,{d.id},{'P1'},None,{'components'})
    assert {x['supplier_code'] for x in out['items']}=={'SUP1'}


def test_project_workspace_adds_supplier_gate_only_when_configured():
    db=_db(); p,d,cad=_project(db, 'LOC7')
    first=project_workspace(db,p,{d.id,cad.id},manufacturing_area='components',identity_groups=['engineering-ai-users'])
    assert first['readiness']['gates']['suppliers'] is None
    db.add(LocalizationItem(project_code=p.code,manufacturing_area='components',part_number='P1',supplier_code='SUP1',supplier_name='Supplier'))
    db.commit()
    second=project_workspace(db,p,{d.id,cad.id},manufacturing_area='components',identity_groups=['engineering-ai-users'])
    assert second['readiness']['gates']['suppliers'] is not None
    assert second['supplier_localization']['configured'] is True
    assert any(x['type']=='supplier' for x in second['readiness']['blockers'])


def test_localization_evidence_pack_freezes_readiness_snapshot():
    db=_db(); p,d,_=_project(db, 'LOC8')
    item=LocalizationItem(project_code=p.code,manufacturing_area='components',part_number='P1',revision='A',supplier_code='SUP1',supplier_name='Supplier',evidence_document_ids=[d.id])
    db.add(item); db.commit(); db.refresh(item)
    ws=supplier_localization_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    pack=create_localization_evidence_pack(db,p.code,item,'engineer',{d.id},ws)
    assert pack.pack_type=='supplier_localization'
    assert pack.manifest['supplier']['code']=='SUP1'
    assert pack.manifest['readiness_snapshot']['score']==ws['items'][0]['supplier_readiness_score']
    assert pack.manifest['governance']['human_supplier_approval_required'] is True
