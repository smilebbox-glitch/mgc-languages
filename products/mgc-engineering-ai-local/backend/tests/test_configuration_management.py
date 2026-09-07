from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureNode, ConfigurationApplicability, Document, DocumentStatus,
    InterfaceDefinition, Project, VehicleVariant,
)
from app.db.session import Base
from app.services.configuration_management import configuration_impact, configuration_workspace
from app.services.project_workspace import project_workspace


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _base(db, code='CFG1'):
    p=Project(code=code,name='Vehicle variants',acl_groups=['engineering-ai-users'])
    d=Document(filename='p1.pdf',stored_path='/tmp/p1',sha256='a'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='drawing',project_code=code,manufacturing_area='assembly',acl_groups=['engineering-ai-users'])
    c=Document(filename='p1.step',stored_path='/tmp/p1.step',sha256='b'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='cad',project_code=code,manufacturing_area='assembly',acl_groups=['engineering-ai-users'])
    db.add_all([p,d,c]); db.commit(); db.refresh(d); db.refresh(c)
    return p,d,c


def test_unknown_variant_is_not_assumed_included():
    db=_db(); p,d,c=_base(db)
    v1=VehicleVariant(project_code=p.code,code='EU-15T',name='EU 1.5T',status='active',market='EU',engine='1.5T')
    v2=VehicleVariant(project_code=p.code,code='RU-20',name='RU 2.0',status='active',market='RU',engine='2.0')
    db.add_all([v1,v2]); db.commit(); db.refresh(v1); db.refresh(v2)
    db.add(ConfigurationApplicability(project_code=p.code,variant_id=v1.id,manufacturing_area='assembly',entity_type='part',entity_key='P1',applicability='included'))
    db.commit()
    out=configuration_impact(db,p.code,'P1',{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert [x['code'] for x in out['affected_variants']]==['EU-15T']
    assert [x['code'] for x in out['unknown_variants']]==['RU-20']
    assert out['unknown_is_not_included'] is True


def test_included_and_excluded_variants_are_separate():
    db=_db(); p,d,c=_base(db,'CFG2')
    a=VehicleVariant(project_code=p.code,code='AT',name='Automatic'); b=VehicleVariant(project_code=p.code,code='MT',name='Manual')
    db.add_all([a,b]);db.commit();db.refresh(a);db.refresh(b)
    db.add_all([
        ConfigurationApplicability(project_code=p.code,variant_id=a.id,entity_type='part',entity_key='P1',applicability='included'),
        ConfigurationApplicability(project_code=p.code,variant_id=b.id,entity_type='part',entity_key='P1',applicability='excluded'),
    ]);db.commit()
    out=configuration_impact(db,p.code,'P1',{d.id,c.id},{'P1'},None,{'assembly'})
    assert {x['code'] for x in out['affected_variants']}=={'AT'}
    assert {x['code'] for x in out['excluded_variants']}=={'MT'}
    assert out['unknown_variants']==[]


def test_interface_applicability_propagates_to_connected_part_impact():
    db=_db(); p,d,c=_base(db,'CFG3')
    n1=ArchitectureNode(project_code=p.code,manufacturing_area='assembly',code='P1N',name='Part',node_type='component',part_number='P1')
    n2=ArchitectureNode(project_code=p.code,manufacturing_area='assembly',code='MATE',name='Mate',node_type='component')
    db.add_all([n1,n2]);db.commit();db.refresh(n1);db.refresh(n2)
    interface=InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF1',name='Joint',source_node_id=n1.id,target_node_id=n2.id)
    variant=VehicleVariant(project_code=p.code,code='AWD',name='AWD')
    db.add_all([interface,variant]);db.commit();db.refresh(interface);db.refresh(variant)
    db.add(ConfigurationApplicability(project_code=p.code,variant_id=variant.id,entity_type='interface',entity_key=interface.id,applicability='included'))
    db.commit()
    out=configuration_impact(db,p.code,'P1',{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert {x['code'] for x in out['affected_variants']}=={'AWD'}
    assert {x['code'] for x in out['indirect_interface_variants']}=={'AWD'}


def test_hidden_variant_evidence_fails_closed():
    db=_db(); p,d,c=_base(db,'CFG4')
    secret=Document(filename='secret.pdf',stored_path='/tmp/secret',sha256='c'*64,status=DocumentStatus.ready,project_code=p.code,acl_groups=['secret'])
    db.add(secret);db.commit();db.refresh(secret)
    v=VehicleVariant(project_code=p.code,code='SECRET',name='Secret variant',evidence_document_ids=[secret.id])
    db.add(v);db.commit()
    out=configuration_workspace(db,p.code,{d.id,c.id},{'P1'},None,{'assembly'})
    assert out['variants']==[]


def test_project_workspace_adds_configuration_gate_only_when_configured():
    db=_db(); p,d,c=_base(db,'CFG5')
    first=project_workspace(db,p,{d.id,c.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    assert first['readiness']['gates']['configurations'] is None
    db.add(VehicleVariant(project_code=p.code,manufacturing_area='assembly',code='BASE',name='Base variant',status='active'))
    db.commit()
    second=project_workspace(db,p,{d.id,c.id},manufacturing_area='assembly',identity_groups=['engineering-ai-users'])
    assert second['readiness']['gates']['configurations'] is not None
    assert second['configurations']['configured'] is True
    assert any(x['type']=='configuration' for x in second['readiness']['blockers'])


def test_released_variant_without_evidence_is_visible_gap():
    db=_db(); p,d,c=_base(db,'CFG6')
    v=VehicleVariant(project_code=p.code,code='REL',name='Released variant',status='released')
    db.add(v);db.commit()
    out=configuration_workspace(db,p.code,{d.id,c.id},{'P1'},None,{'assembly'})
    assert any(x['type']=='variant_evidence' for x in out['gaps'])

def test_explicit_part_exclusion_overrides_interface_inference():
    db=_db(); p,d,c=_base(db,'CFG7')
    n1=ArchitectureNode(project_code=p.code,manufacturing_area='assembly',code='P1N',name='Part',node_type='component',part_number='P1')
    n2=ArchitectureNode(project_code=p.code,manufacturing_area='assembly',code='MATE',name='Mate',node_type='component')
    db.add_all([n1,n2]);db.commit();db.refresh(n1);db.refresh(n2)
    interface=InterfaceDefinition(project_code=p.code,manufacturing_area='assembly',code='IF7',name='Joint',source_node_id=n1.id,target_node_id=n2.id)
    variant=VehicleVariant(project_code=p.code,code='VAR7',name='Variant 7')
    db.add_all([interface,variant]);db.commit();db.refresh(interface);db.refresh(variant)
    db.add_all([
        ConfigurationApplicability(project_code=p.code,variant_id=variant.id,entity_type='interface',entity_key=interface.id,applicability='included'),
        ConfigurationApplicability(project_code=p.code,variant_id=variant.id,entity_type='part',entity_key='P1',applicability='excluded'),
    ]);db.commit()
    out=configuration_impact(db,p.code,'P1',{d.id,c.id},{'P1'},'assembly',{'assembly'})
    assert out['affected_variants']==[]
    assert {x['code'] for x in out['excluded_variants']}=={'VAR7'}
