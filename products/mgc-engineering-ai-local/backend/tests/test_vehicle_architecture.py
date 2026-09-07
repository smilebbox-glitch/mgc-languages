from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureNode, InterfaceDefinition, InterfaceVerification, Document, DocumentStatus,
    Project, EngineeringRequirement, RequirementVerification, ChangeRequest, CostBaseline, CostLine,
    LocalizationItem,
)
from app.db.session import Base
from app.services.vehicle_architecture import vehicle_architecture_workspace, architecture_impact, interface_fingerprint
from app.services.project_workspace import project_workspace


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _base(db: Session, code='ARCH1'):
    p=Project(code=code,name='Vehicle architecture',acl_groups=['engineering-ai-users'])
    d=Document(filename='p1.pdf',stored_path='/tmp/p1',sha256='a'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='drawing',project_code=code,manufacturing_area='assembly',acl_groups=['engineering-ai-users'])
    c=Document(filename='p1.step',stored_path='/tmp/p1.step',sha256='b'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='cad',project_code=code,manufacturing_area='assembly',acl_groups=['engineering-ai-users'])
    db.add_all([p,d,c]); db.commit(); db.refresh(d); db.refresh(c)
    return p,d,c


def _nodes(db, project_code):
    vehicle=ArchitectureNode(project_code=project_code,code='VEH',name='Vehicle',node_type='vehicle')
    sys=ArchitectureNode(project_code=project_code,code='EXH',name='Exhaust',node_type='system',parent_node_id=None)
    part=ArchitectureNode(project_code=project_code,manufacturing_area='assembly',code='EXH-FLG',name='Exhaust flange',node_type='component',part_number='P1')
    mate=ArchitectureNode(project_code=project_code,manufacturing_area='assembly',code='ENG-MATE',name='Engine mating flange',node_type='component')
    db.add_all([vehicle,sys,part,mate]); db.commit()
    sys.parent_node_id=vehicle.id; part.parent_node_id=sys.id; mate.parent_node_id=vehicle.id; db.commit()
    return vehicle,sys,part,mate


def test_critical_interface_without_requirement_and_verification_is_blocker():
    db=_db(); p,d,c=_base(db); _,_,part,mate=_nodes(db,p.code)
    db.add(InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF-01',name='Flange joint',interface_type='mechanical',source_node_id=part.id,target_node_id=mate.id,criticality='critical'))
    db.commit()
    out=vehicle_architecture_workspace(db,p.code,{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert out['configured'] is True
    assert out['status']=='blocked'
    assert any(x['type']=='interface_requirement' and x['severity']=='critical' for x in out['gaps'])
    assert any(x['type']=='interface_unverified' for x in out['gaps'])


def test_passed_interface_verification_without_proof_is_not_effective():
    db=_db(); p,d,c=_base(db,'ARCH2'); _,_,part,mate=_nodes(db,p.code)
    i=InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF-02',name='Joint',source_node_id=part.id,target_node_id=mate.id,criticality='high')
    db.add(i);db.commit();db.refresh(i)
    nodes={x.id:x for x in [part,mate]}
    db.add(InterfaceVerification(project_code=p.code,interface_id=i.id,manufacturing_area='assembly',code='IV-02',title='Fit check',status='passed',interface_fingerprint_snapshot=interface_fingerprint(i,nodes)))
    db.commit()
    out=vehicle_architecture_workspace(db,p.code,{d.id,c.id},{'P1'},'assembly',{'assembly'})
    v=out['interfaces'][0]['verifications'][0]
    assert v['proof_ok'] is False
    assert v['effective_pass'] is False
    assert any(x['type']=='interface_evidence' for x in out['gaps'])


def test_interface_verification_becomes_stale_when_endpoint_changes():
    db=_db(); p,d,c=_base(db,'ARCH3'); _,_,part,mate=_nodes(db,p.code)
    i=InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF-03',name='Joint',source_node_id=part.id,target_node_id=mate.id,evidence_document_ids=[d.id])
    db.add(i);db.commit();db.refresh(i)
    allnodes={x.id:x for x in db.query(ArchitectureNode).filter(ArchitectureNode.project_code==p.code).all()}
    v=InterfaceVerification(project_code=p.code,interface_id=i.id,manufacturing_area='assembly',code='IV-03',title='Review',status='passed',evidence_document_ids=[d.id],interface_fingerprint_snapshot=interface_fingerprint(i,allnodes))
    db.add(v);db.commit()
    first=vehicle_architecture_workspace(db,p.code,{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert first['interfaces'][0]['verifications'][0]['effective_pass'] is True
    part.name='Changed flange'; db.commit(); db.refresh(part)
    second=vehicle_architecture_workspace(db,p.code,{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert second['interfaces'][0]['verifications'][0]['stale'] is True
    assert any(x['type']=='interface_stale' for x in second['gaps'])


def test_requirement_verification_can_prove_interface():
    db=_db(); p,d,c=_base(db,'ARCH4'); _,_,part,mate=_nodes(db,p.code)
    r=EngineeringRequirement(project_code=p.code,manufacturing_area='assembly',code='REQ-IF',title='Flange interface',requirement_text='Joint shall seal',source_document_id=d.id,part_numbers=['P1'])
    db.add(r);db.commit();db.refresh(r)
    rv=RequirementVerification(project_code=p.code,requirement_id=r.id,manufacturing_area='assembly',code='RV-IF',title='Seal test',status='passed',evidence_document_ids=[d.id],requirement_updated_at_snapshot=r.updated_at,source_document_sha256_snapshot=d.sha256)
    db.add(rv);db.commit();db.refresh(rv)
    i=InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF-04',name='Sealed flange',source_node_id=part.id,target_node_id=mate.id,criticality='critical',requirement_ids=[r.id])
    db.add(i);db.commit();db.refresh(i)
    allnodes={x.id:x for x in db.query(ArchitectureNode).filter(ArchitectureNode.project_code==p.code).all()}
    db.add(InterfaceVerification(project_code=p.code,interface_id=i.id,manufacturing_area='assembly',code='IV-04',title='Use requirement proof',status='passed',linked_requirement_verification_id=rv.id,interface_fingerprint_snapshot=interface_fingerprint(i,allnodes)))
    db.commit()
    out=vehicle_architecture_workspace(db,p.code,{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert out['interfaces'][0]['verifications'][0]['effective_pass'] is True
    assert not any(x['type'] in {'interface_requirement','interface_unverified','interface_evidence'} for x in out['gaps'])


def test_architecture_respects_area_and_hidden_part_evidence():
    db=_db(); p,d,c=_base(db,'ARCH5'); _,_,part,mate=_nodes(db,p.code)
    hidden_doc=Document(filename='paint.pdf',stored_path='/tmp/paint',sha256='c'*64,status=DocumentStatus.ready,part_number='P2',revision='A',doc_type='drawing',project_code=p.code,manufacturing_area='paint',acl_groups=['paint-secret'])
    db.add(hidden_doc);db.commit();db.refresh(hidden_doc)
    hidden=ArchitectureNode(project_code=p.code,manufacturing_area='paint',code='PAINT',name='Secret Paint',node_type='system',part_number='P2',evidence_document_ids=[hidden_doc.id])
    db.add(hidden);db.commit()
    out=vehicle_architecture_workspace(db,p.code,{d.id,c.id},{'P1'},None,{'assembly'})
    assert 'PAINT' not in {x['code'] for x in out['nodes']}
    assert 'EXH-FLG' in {x['code'] for x in out['nodes']}


def test_architecture_impact_connects_interface_change_cost_and_localization():
    db=_db(); p,d,c=_base(db,'ARCH6'); _,_,part,mate=_nodes(db,p.code)
    ch=ChangeRequest(code='ECR-ARCH',title='Change flange',part_number='P1',status='impact_review')
    db.add(ch);db.commit();db.refresh(ch)
    i=InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF-06',name='Flange interface',source_node_id=part.id,target_node_id=mate.id,linked_change_ids=[ch.id])
    db.add(i)
    b=CostBaseline(project_code=p.code,code='CUR',name='Current',baseline_type='current');db.add(b);db.commit();db.refresh(b)
    db.add(CostLine(project_code=p.code,baseline_id=b.id,manufacturing_area='assembly',part_number='P1',calculation_mode='quote',supplier_unit_price=100))
    db.add(LocalizationItem(project_code=p.code,manufacturing_area='assembly',part_number='P1',supplier_code='SUP1',supplier_name='Supplier'))
    db.commit()
    out=architecture_impact(db,p.code,'P1',{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert len(out['connected_interfaces'])==1
    assert out['adjacent_nodes'][0]['code']=='ENG-MATE'
    assert out['open_changes'][0]['id']==ch.id
    assert len(out['cost_line_ids'])==1
    assert len(out['localization_item_ids'])==1


def test_project_workspace_adds_architecture_gate_only_when_configured():
    db=_db(); p,d,c=_base(db,'ARCH7')
    first=project_workspace(db,p,{d.id,c.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    assert first['readiness']['gates']['architecture'] is None
    _,_,part,mate=_nodes(db,p.code)
    db.add(InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF-07',name='Critical joint',source_node_id=part.id,target_node_id=mate.id,criticality='critical'))
    db.commit()
    second=project_workspace(db,p,{d.id,c.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    assert second['readiness']['gates']['architecture'] is not None
    assert second['vehicle_architecture']['configured'] is True
    assert any(x['type']=='architecture' for x in second['readiness']['blockers'])

def test_architecture_with_mixed_visible_and_hidden_evidence_fails_closed():
    db=_db(); p,d,c=_base(db,'ARCH8')
    hidden=Document(filename='secret.pdf',stored_path='/tmp/secret',sha256='9'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='spec',project_code=p.code,manufacturing_area='assembly',acl_groups=['secret-group'])
    db.add(hidden); db.commit(); db.refresh(hidden)
    n=ArchitectureNode(project_code=p.code,manufacturing_area='assembly',code='MIXED',name='Mixed evidence node',node_type='component',part_number='P1',evidence_document_ids=[d.id,hidden.id])
    db.add(n); db.commit()
    out=vehicle_architecture_workspace(db,p.code,{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert 'MIXED' not in {x['code'] for x in out['nodes']}
