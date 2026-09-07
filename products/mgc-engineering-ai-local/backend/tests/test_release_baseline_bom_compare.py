from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import BOMItem, Document, DocumentStatus, Project, ReleaseBaseline, VehicleVariant, ConfigurationApplicability
from app.db.session import Base
from app.services.release_baseline import (
    compare_bom_versions, create_release_baseline, list_bom_versions,
    release_workspace, serialize_release_baseline,
)
from app.services.project_workspace import project_workspace


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _doc(db, project, filename, revision, sha, doc_type='bom'):
    d=Document(filename=filename,stored_path=f'/tmp/{filename}',sha256=sha,status=DocumentStatus.ready,part_number='ROOT',revision=revision,doc_type=doc_type,project_code=project.code,manufacturing_area='assembly',acl_groups=['engineering-ai-users'])
    db.add(d);db.commit();db.refresh(d);return d


def _item(db, doc, child, rev, qty, pos, supplier=None, cost=None):
    x=BOMItem(parent_part_number='ROOT',parent_revision=doc.revision,child_part_number=child,child_revision=rev,quantity=qty,unit='pcs',position=pos,supplier_code=supplier,supplier_name=supplier,unit_cost=cost,currency='RUB' if cost is not None else None,source_document_id=doc.id)
    db.add(x);return x


def test_bom_compare_detects_added_removed_replaced_and_field_changes():
    db=_db();p=Project(code='BOM49',name='BOM compare',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    a=_doc(db,p,'bom_A.csv','A','a'*64);b=_doc(db,p,'bom_B.csv','B','b'*64)
    _item(db,a,'P1','A',1,'10','SUP-A',100);_item(db,a,'P2','A',2,'20','SUP-B',200);_item(db,a,'P4','A',1,'40')
    _item(db,b,'P1','B',3,'10','SUP-C',120);_item(db,b,'P3','A',1,'20','SUP-D',300);_item(db,b,'P5','A',1,'50')
    db.commit()
    out=compare_bom_versions(db,p.code,{a.id,b.id},a.id,b.id,'ROOT')
    assert out['summary']=={'added':1,'removed':1,'replaced':1,'moved':0,'changed':1,'unchanged':0}
    assert out['replaced'][0]['position']=='20'
    assert out['replaced'][0]['from']['child_part_number']=='P2'
    assert out['replaced'][0]['to']['child_part_number']=='P3'
    changes=out['changed'][0]['changes']
    assert changes['child_revision']=={'from':'A','to':'B'}
    assert changes['quantity']=={'from':1.0,'to':3.0}
    assert changes['supplier_code']=={'from':'SUP-A','to':'SUP-C'}
    assert changes['unit_cost']=={'from':100.0,'to':120.0}


def test_list_bom_versions_is_document_hash_backed():
    db=_db();p=Project(code='BOMV',name='Versions',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    a=_doc(db,p,'bom_A.csv','A','1'*64);_item(db,a,'P1','A',1,'10');db.commit()
    rows=list_bom_versions(db,p.code,{a.id},'ROOT')
    assert len(rows)==1
    assert rows[0]['version_label']=='A'
    assert rows[0]['sha256']=='1'*64
    assert len(rows[0]['fingerprint'])==64


def test_release_baseline_is_immutable_snapshot_and_workspace_visible():
    db=_db();p=Project(code='REL49',name='Release baseline',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    d=_doc(db,p,'bom_A.csv','A','2'*64);_item(db,d,'P1','A',1,'10');db.commit()
    row=create_release_baseline(db,p,code='DF-01',name='Design Freeze 01',baseline_type='design_freeze',created_by='eng1',visible_document_ids={d.id},visible_part_numbers={'ROOT'},allowed_area_codes={'assembly'},manufacturing_area='assembly')
    first=row.fingerprint
    # Later BOM mutation cannot mutate the frozen snapshot.
    _item(db,d,'P2','A',1,'20');db.commit();db.refresh(row)
    assert row.fingerprint==first
    assert len((row.snapshot_json or {})['bom'])==1
    ws=release_workspace(db,p.code,{d.id},'ROOT')
    assert ws['counts']['baselines']==1
    assert ws['baselines'][0]['code']=='DF-01'


def test_release_baseline_with_hidden_source_fails_closed_for_other_viewer():
    db=_db();p=Project(code='RELSEC',name='Security',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    d=_doc(db,p,'secret_bom.csv','A','3'*64);_item(db,d,'P1','A',1,'10');db.commit()
    row=create_release_baseline(db,p,code='DF-SEC',name='Secret',baseline_type='design_freeze',created_by='eng1',visible_document_ids={d.id},visible_part_numbers={'ROOT'},allowed_area_codes={'assembly'})
    try:
        serialize_release_baseline(row,set(),True)
        assert False, 'baseline with hidden evidence must fail closed'
    except LookupError:
        pass


def test_variant_baseline_marks_unknown_applicability_not_release_candidate():
    db=_db();p=Project(code='RELVAR',name='Variant baseline',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    root=_doc(db,p,'root.pdf','A','4'*64,'drawing')
    p1=Document(filename='p1.pdf',stored_path='/tmp/p1',sha256='5'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='drawing',project_code=p.code,manufacturing_area='assembly',acl_groups=['engineering-ai-users'])
    db.add(p1);db.commit();db.refresh(p1)
    v=VehicleVariant(project_code=p.code,code='EU',name='EU',status='active');db.add(v);db.commit();db.refresh(v)
    # ROOT explicitly included; P1 remains UNKNOWN.
    db.add(ConfigurationApplicability(project_code=p.code,variant_id=v.id,entity_type='part',entity_key='ROOT',applicability='included'));db.commit()
    row=create_release_baseline(db,p,code='REL-EU',name='EU snapshot',baseline_type='release',created_by='admin',visible_document_ids={root.id,p1.id},visible_part_numbers={'ROOT','P1'},allowed_area_codes={'assembly'},variant_id=v.id)
    assert row.release_candidate is False
    assert any('UNKNOWN' in x for x in (row.metadata_json or {}).get('warnings',[]))


def test_project_workspace_exposes_release_traceability_without_changing_readiness_gate():
    db=_db();p=Project(code='RELWS',name='Workspace',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    d=_doc(db,p,'bom.csv','A','6'*64);_item(db,d,'P1','A',1,'10');db.commit()
    before=project_workspace(db,p,{d.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    create_release_baseline(db,p,code='AUD-01',name='Audit',baseline_type='audit',created_by='eng',visible_document_ids={d.id},visible_part_numbers={'ROOT'},allowed_area_codes={'assembly'},manufacturing_area='assembly')
    after=project_workspace(db,p,{d.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    assert after['release_traceability']['counts']['baselines']==1
    assert before['readiness']['score']==after['readiness']['score']


def test_bom_compare_separates_moved_from_field_change():
    db=_db();p=Project(code='BOMMOVE',name='BOM move',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    a=_doc(db,p,'bom_A.csv','A','7'*64);b=_doc(db,p,'bom_B.csv','B','8'*64)
    _item(db,a,'P1','A',1,'10','SUP-A',100);_item(db,b,'P1','A',1,'30','SUP-A',100);db.commit()
    out=compare_bom_versions(db,p.code,{a.id,b.id},a.id,b.id,'ROOT')
    assert out['summary']['moved']==1
    assert out['summary']['changed']==0
    assert out['moved'][0]['from_positions']==['10']
    assert out['moved'][0]['to_positions']==['30']


def test_bom_compare_reports_cost_delta_only_when_pricing_is_complete_and_single_currency():
    db=_db();p=Project(code='BOMCOST',name='BOM cost',root_part_number='ROOT',acl_groups=['engineering-ai-users']);db.add(p);db.commit()
    a=_doc(db,p,'bom_A.csv','A','9'*64);b=_doc(db,p,'bom_B.csv','B','0'*64)
    _item(db,a,'P1','A',2,'10','SUP-A',100);_item(db,b,'P1','A',3,'10','SUP-A',120);db.commit()
    out=compare_bom_versions(db,p.code,{a.id,b.id},a.id,b.id,'ROOT')
    assert out['cost']['comparable'] is True
    assert out['cost']['currency']=='RUB'
    assert out['cost']['left']['totals']['RUB']==200.0
    assert out['cost']['right']['totals']['RUB']==360.0
    assert out['cost']['delta']==160.0
