from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import CostBaseline, CostLine, Document, DocumentStatus, Project, SupplierQuotation, ChangeRequest
from app.db.session import Base
from app.services.cost_economics import cost_economics_workspace, create_cost_evidence_pack, line_calculation
from app.services.project_workspace import project_workspace


def _db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _project(db: Session, code='COST1'):
    p=Project(code=code,name='Cost project',acl_groups=['engineering-ai-users'])
    d=Document(filename='p1.pdf',stored_path='/tmp/p1',sha256='a'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='drawing',project_code=code,manufacturing_area='components',acl_groups=['engineering-ai-users'])
    cad=Document(filename='p1.step',stored_path='/tmp/p1.step',sha256='b'*64,status=DocumentStatus.ready,part_number='P1',revision='A',doc_type='cad',project_code=code,manufacturing_area='components',acl_groups=['engineering-ai-users'])
    db.add_all([p,d,cad]); db.commit(); db.refresh(d); db.refresh(cad)
    return p,d,cad


def test_breakdown_cost_is_deterministic_and_tooling_only_amortized_with_explicit_volume():
    db=_db(); p,d,_=_project(db)
    b=CostBaseline(project_code=p.code,manufacturing_area='components',code='CUR',name='Current',baseline_type='current',status='active',currency='RUB',annual_volume=10000)
    db.add(b); db.commit(); db.refresh(b)
    l=CostLine(project_code=p.code,baseline_id=b.id,manufacturing_area='components',part_number='P1',quantity_per_vehicle=2,
               mass_kg=1.0,material_price_per_kg=100.0,scrap_rate_pct=10,conversion_cost=20,logistics_cost=5,packaging_cost=2,overhead_cost=3,other_unit_cost=1,
               tooling_cost=10000,tooling_amortization_volume=10000,target_unit_cost=130)
    calc=line_calculation(l)
    # 100 material + 10% scrap + 20 + 5 + 2 + 3 + 1 + 1 tooling = 142/unit; x2/vehicle
    assert calc['unit_cost']==142.0
    assert calc['vehicle_cost']==284.0
    assert calc['tooling_amortized_unit']==1.0
    assert calc['variance_to_target']==12.0


def test_quote_mode_does_not_double_count_material_or_conversion():
    db=_db(); p,_,_=_project(db,'COST2')
    b=CostBaseline(project_code=p.code,code='QUOTE',name='Quote',baseline_type='current',status='active')
    db.add(b); db.commit(); db.refresh(b)
    l=CostLine(project_code=p.code,baseline_id=b.id,part_number='P1',calculation_mode='quote',supplier_unit_price=500,
               mass_kg=10,material_price_per_kg=100,conversion_cost=999,logistics_cost=20,packaging_cost=5,other_unit_cost=1)
    calc=line_calculation(l)
    assert calc['unit_cost']==526.0
    assert calc['source']=='supplier_quote'


def test_current_vs_target_and_annual_variance():
    db=_db(); p,d,_=_project(db,'COST3')
    target=CostBaseline(project_code=p.code,manufacturing_area='components',code='TARGET',name='Target',baseline_type='target',status='frozen',currency='RUB',annual_volume=100000)
    current=CostBaseline(project_code=p.code,manufacturing_area='components',code='CURRENT',name='Current',baseline_type='current',status='active',currency='RUB',annual_volume=100000)
    db.add_all([target,current]); db.commit(); db.refresh(target); db.refresh(current)
    db.add_all([
        CostLine(project_code=p.code,baseline_id=target.id,manufacturing_area='components',part_number='P1',calculation_mode='quote',supplier_unit_price=100),
        CostLine(project_code=p.code,baseline_id=current.id,manufacturing_area='components',part_number='P1',calculation_mode='quote',supplier_unit_price=110),
    ]); db.commit()
    out=cost_economics_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    assert out['current_vehicle_cost']==110.0
    assert out['target_vehicle_cost']==100.0
    assert out['variance_to_target']==10.0
    assert out['variance_to_target_pct']==10.0
    assert out['annual_variance']==1000000.0


def test_over_target_alert_is_advisory_not_project_release_gate():
    db=_db(); p,d,cad=_project(db,'COST4')
    before=project_workspace(db,p,{d.id,cad.id},manufacturing_area='components',identity_groups=['engineering-ai-users'])
    target=CostBaseline(project_code=p.code,manufacturing_area='components',code='TGT',name='Target',baseline_type='target',status='active')
    cur=CostBaseline(project_code=p.code,manufacturing_area='components',code='CUR',name='Current',baseline_type='current',status='active')
    db.add_all([target,cur]); db.commit(); db.refresh(target); db.refresh(cur)
    db.add_all([
        CostLine(project_code=p.code,baseline_id=target.id,manufacturing_area='components',part_number='P1',calculation_mode='quote',supplier_unit_price=100),
        CostLine(project_code=p.code,baseline_id=cur.id,manufacturing_area='components',part_number='P1',calculation_mode='quote',supplier_unit_price=130),
    ]); db.commit()
    after=project_workspace(db,p,{d.id,cad.id},manufacturing_area='components',identity_groups=['engineering-ai-users'])
    assert after['cost_economics']['configured'] is True
    assert any(x['type']=='over_target' for x in after['cost_economics']['gaps'])
    assert before['readiness']['score']==after['readiness']['score']
    assert not any(x['type']=='cost' for x in after['readiness']['blockers'])


def test_change_cost_scenario_calculates_ecr_eco_impact():
    db=_db(); p,d,_=_project(db,'COST5')
    ch=ChangeRequest(code='ECR-COST5',title='Thickness change',part_number='P1',status='impact_review')
    db.add(ch); db.commit(); db.refresh(ch)
    cur=CostBaseline(project_code=p.code,code='CUR',name='Current',baseline_type='current',status='active',annual_volume=50000)
    db.add(cur); db.commit(); db.refresh(cur)
    change=CostBaseline(project_code=p.code,code='CHG',name='After ECR',baseline_type='change',status='active',annual_volume=50000,reference_baseline_id=cur.id,linked_change_id=ch.id)
    db.add(change); db.commit(); db.refresh(change)
    db.add_all([
        CostLine(project_code=p.code,baseline_id=cur.id,part_number='P1',calculation_mode='quote',supplier_unit_price=200),
        CostLine(project_code=p.code,baseline_id=change.id,part_number='P1',calculation_mode='quote',supplier_unit_price=212),
    ]); db.commit()
    out=cost_economics_workspace(db,p.code,{d.id},{'P1'},None,{'components'})
    impact=out['change_impacts'][0]
    assert impact['linked_change_id']==ch.id
    assert impact['unit_delta_per_vehicle']==12.0
    assert impact['annual_delta']==600000.0


def test_expired_selected_supplier_quote_is_visible_gap():
    db=_db(); p,d,_=_project(db,'COST6')
    db.add(SupplierQuotation(project_code=p.code,manufacturing_area='components',code='Q1',part_number='P1',supplier_code='SUP1',supplier_name='Supplier',currency='RUB',unit_price=100,status='selected',valid_until=datetime.now(timezone.utc)-timedelta(days=1)))
    db.commit()
    out=cost_economics_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    assert out['quotes'][0]['expired'] is True
    assert any(x['type']=='selected_quote_expired' for x in out['gaps'])


def test_cost_economics_respects_area_and_visible_parts():
    db=_db(); p,d,_=_project(db,'COST7')
    hidden=Document(filename='p2.pdf',stored_path='/tmp/p2',sha256='c'*64,status=DocumentStatus.ready,part_number='P2',revision='A',doc_type='drawing',project_code=p.code,manufacturing_area='paint',acl_groups=['paint-secret'])
    db.add(hidden)
    b1=CostBaseline(project_code=p.code,manufacturing_area='components',code='C1',name='Components',baseline_type='current')
    b2=CostBaseline(project_code=p.code,manufacturing_area='paint',code='C2',name='Paint',baseline_type='current')
    db.add_all([b1,b2]); db.commit(); db.refresh(b1); db.refresh(b2)
    db.add_all([
        CostLine(project_code=p.code,baseline_id=b1.id,manufacturing_area='components',part_number='P1',calculation_mode='quote',supplier_unit_price=100),
        CostLine(project_code=p.code,baseline_id=b2.id,manufacturing_area='paint',part_number='P2',calculation_mode='quote',supplier_unit_price=999),
    ]); db.commit()
    out=cost_economics_workspace(db,p.code,{d.id},{'P1'},None,{'components'})
    assert {x['code'] for x in out['baselines']}=={'C1'}
    assert out['current_vehicle_cost']==100.0


def test_cost_evidence_pack_freezes_snapshot():
    db=_db(); p,d,_=_project(db,'COST8')
    b=CostBaseline(project_code=p.code,manufacturing_area='components',code='CUR',name='Current',baseline_type='current',status='active',currency='RUB',evidence_document_ids=[d.id])
    db.add(b); db.commit(); db.refresh(b)
    db.add(CostLine(project_code=p.code,baseline_id=b.id,manufacturing_area='components',part_number='P1',calculation_mode='quote',supplier_unit_price=123))
    db.commit()
    ws=cost_economics_workspace(db,p.code,{d.id},{'P1'},'components',{'components'})
    pack=create_cost_evidence_pack(db,p.code,b,'engineer',{d.id},ws)
    assert pack.pack_type=='engineering_cost'
    assert pack.manifest['baseline']['vehicle_cost']==123.0
    assert pack.manifest['governance']['finance_approval_required'] is True
