from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    BuildGenealogyItem, ControlPlanItem, Document, DocumentStatus, FieldQualityClaim,
    ManufacturingLine, Part, PFMEAItem, ProcessAsset, ProcessCapabilityRecord,
    ProcessOperation, ProcessStation, Project, ProjectArea, SeriesContainmentCase,
    SeriesQualityObservation, VehicleBuild, VehicleVariant,
)
from app.db.session import Base
from app.services.series_quality_manufacturing_intelligence import (
    series_intelligence_answer, series_quality_workspace, suspect_population, visible_series_rows,
)


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session, code='S57'):
    p=Project(code=code,name='Series',acl_groups=['engineering-ai-users'])
    area=ProjectArea(project_code=code,code='assembly',name='Assembly',acl_groups=['engineering-ai-users'])
    part=Part(part_number=f'PART-{code}',name='Bracket',project_code=code,latest_revision='D',metadata_json={'manufacturing_area':'assembly'})
    doc=Document(filename='series.pdf',stored_path='/tmp/series.pdf',sha256='a'*64,status=DocumentStatus.ready,part_number=part.part_number,revision='D',doc_type='drawing',project_code=code,manufacturing_area='assembly',acl_groups=['engineering-ai-users'])
    line=ManufacturingLine(project_code=code,manufacturing_area='assembly',code='L1',name='Line 1')
    db.add_all([p,area,part,doc,line]);db.commit();db.refresh(doc);db.refresh(line)
    st=ProcessStation(line_id=line.id,code='ST1',name='Station 1');db.add(st);db.commit();db.refresh(st)
    op=ProcessOperation(station_id=st.id,code='OP1',name='Weld bracket',part_number=part.part_number);db.add(op);db.commit();db.refresh(op)
    asset=ProcessAsset(operation_id=op.id,code='FX1',name='Fixture',asset_type='fixture',calibration_due_at=datetime.now(timezone.utc)-timedelta(days=2),maintenance_due_at=datetime.now(timezone.utc)+timedelta(days=5));db.add(asset);db.commit();db.refresh(asset)
    v=VehicleVariant(project_code=code,manufacturing_area='assembly',code='PREM',name='Premium',status='released',evidence_document_ids=[doc.id]);db.add(v);db.commit();db.refresh(v)
    return p,part,doc,line,st,op,asset,v


def _ws(db,p,part,doc):
    return series_quality_workspace(db,p.code,{doc.id},{part.part_number},'assembly',{'assembly'})


def _obs(db,p,part,doc,**kw):
    defaults=dict(project_code=p.code,manufacturing_area='assembly',part_number=part.part_number,revision='D',inspected_quantity=1000,defect_quantity=2,observed_at=datetime.now(timezone.utc),source_system='qms',evidence_document_ids=[doc.id])
    defaults.update(kw); row=SeriesQualityObservation(**defaults);db.add(row);db.commit();db.refresh(row);return row


def test_series_health_uses_actual_series_observations():
    db=_db();p,part,doc,*rest=_seed(db)
    _obs(db,p,part,doc,inspected_quantity=1000,defect_quantity=3,produced_quantity=1000)
    out=_ws(db,p,part,doc)
    assert out['series_health']['product_quality']['defect_rate_pct']==0.3
    assert out['series_health']['product_quality']['band']=='GREEN'
    assert out['counts']['observations']==1


def test_capability_degradation_is_visible_and_not_auto_approved():
    db=_db();p,part,doc,line,st,op,asset,v=_seed(db,'CP57')
    t=datetime.now(timezone.utc)
    db.add_all([
        ProcessCapabilityRecord(project_code=p.code,manufacturing_area='assembly',station_id=st.id,operation_id=op.id,asset_id=asset.id,part_number=part.part_number,characteristic='Door gap',sample_size=50,cpk=1.45,measured_at=t-timedelta(days=2),evidence_document_ids=[doc.id]),
        ProcessCapabilityRecord(project_code=p.code,manufacturing_area='assembly',station_id=st.id,operation_id=op.id,asset_id=asset.id,part_number=part.part_number,characteristic='Door gap',sample_size=50,cpk=0.88,measured_at=t,evidence_document_ids=[doc.id]),
    ]);db.commit()
    c=_ws(db,p,part,doc)['capability'][0]
    assert c['status']=='RED' and c['trend']=='DEGRADING' and c['previous_cpk']==1.45


def test_change_point_is_explainable_and_correlation_only():
    db=_db();p,part,doc,*rest=_seed(db,'CHP57');t=datetime.now(timezone.utc)-timedelta(days=6)
    for i,(defs,lot) in enumerate([(1,'A'),(1,'A'),(8,'B'),(10,'B')]):
        _obs(db,p,part,doc,defect_code='GAP',supplier_code='SUP1',supplier_lot=lot,inspected_quantity=1000,defect_quantity=defs,observed_at=t+timedelta(days=i))
    cp=_ws(db,p,part,doc)['change_points'][0]
    assert cp['recent_rate_pct']>cp['baseline_rate_pct']*2
    assert cp['causal_claim'] is False and cp['correlation_only'] is True
    assert any(x['type']=='supplier_lot' and x['after']=='B' for x in cp['associations'])


def test_suspect_population_filters_vin_by_supplier_lot():
    db=_db();p,part,doc,line,st,op,asset,v=_seed(db,'VIN57')
    for idx,lot in enumerate(['GOOD','BAD','BAD']):
        b=VehicleBuild(project_code=p.code,manufacturing_area='assembly',code=f'S{idx}',vehicle_identifier=f'VIN{idx}',variant_id=v.id,plant='Kaluga',build_type='series_observation',status='completed',completed_at=datetime.now(timezone.utc)+timedelta(minutes=idx),evidence_document_ids=[doc.id]);db.add(b);db.commit();db.refresh(b)
        db.add(BuildGenealogyItem(build_id=b.id,manufacturing_area='assembly',part_number=part.part_number,revision='D',supplier_code='SUP1',lot_number=lot,source_system='mes',evidence_document_ids=[doc.id]));db.commit()
    out=suspect_population(db,p.code,{doc.id},{part.part_number},{'assembly'},{'part_number':part.part_number,'supplier_code':'SUP1','supplier_lot':'BAD'},'assembly')
    assert out['suspect_vehicle_count']==2
    assert {x['vehicle_identifier'] for x in out['vehicles']}=={'VIN1','VIN2'}


def test_containment_progress_is_human_controlled():
    db=_db();p,part,doc,*rest=_seed(db,'CON57')
    db.add(SeriesContainmentCase(project_code=p.code,manufacturing_area='assembly',code='CT1',title='100% inspect',part_number=part.part_number,status='contained',suspect_vehicle_identifiers=['V1','V2','V3','V4'],inspected_quantity=3,defect_quantity=1,evidence_document_ids=[doc.id]));db.commit()
    c=_ws(db,p,part,doc)['containments'][0]
    assert c['remaining_quantity']==1 and c['inspection_progress_pct']==75.0
    assert c['human_status_control_required'] is True


def test_pfmea_control_plan_actual_defect_loop_requests_human_review():
    db=_db();p,part,doc,line,st,op,asset,v=_seed(db,'PF57')
    pf=PFMEAItem(project_code=p.code,manufacturing_area='assembly',part_number=part.part_number,process_step='weld',process_operation_id=op.id,failure_mode='weld crack',occurrence=1,detection=3,severity=8,evidence_document_ids=[doc.id])
    cp=ControlPlanItem(project_code=p.code,manufacturing_area='assembly',part_number=part.part_number,process_step='weld',process_operation_id=op.id,characteristic='weld crack inspection',status='approved',evidence_document_ids=[doc.id])
    db.add_all([pf,cp]);db.commit()
    for i in range(2): _obs(db,p,part,doc,operation_id=op.id,defect_code='weld crack',inspected_quantity=500,defect_quantity=3)
    row=_ws(db,p,part,doc)['pfmea_control_defect'][0]
    assert row['review_required'] is True and row['human_pfmea_update_required'] is True
    assert row['control_plan_items']==1


def test_supplier_lot_signal_compares_lot_with_other_lots():
    db=_db();p,part,doc,*rest=_seed(db,'LOT57')
    _obs(db,p,part,doc,supplier_code='SUP1',supplier_lot='A',inspected_quantity=1000,defect_quantity=1)
    _obs(db,p,part,doc,supplier_code='SUP1',supplier_lot='B',inspected_quantity=1000,defect_quantity=12)
    s=_ws(db,p,part,doc)['supplier_lot_intelligence'][0]
    assert s['supplier_lot']=='B' and s['rate_ratio']>=10 and s['causal_claim'] is False


def test_expired_calibration_surfaces_measurements_after_expiry():
    db=_db();p,part,doc,line,st,op,asset,v=_seed(db,'CAL57')
    db.add(ProcessCapabilityRecord(project_code=p.code,manufacturing_area='assembly',station_id=st.id,operation_id=op.id,asset_id=asset.id,part_number=part.part_number,characteristic='Gap',sample_size=117,cpk=1.2,measured_at=datetime.now(timezone.utc),evidence_document_ids=[doc.id]));db.commit()
    sig=_ws(db,p,part,doc)['asset_signals'][0]
    assert 'calibration_expired' in sig['reasons']
    assert sig['samples_after_calibration_expiry']==117 and sig['machine_control'] is False


def test_field_feedback_enters_copq_advisory_layer():
    db=_db();p,part,doc,*rest=_seed(db,'FIELD57')
    _obs(db,p,part,doc,scrap_cost=100,rework_cost=200,containment_cost=300,warranty_cost_estimate=50,currency='RUB')
    db.add_all([
        FieldQualityClaim(project_code=p.code,manufacturing_area='assembly',claim_reference='F1',vehicle_identifier='V1',part_number=part.part_number,supplier_code='SUP1',failure_mode='coolant leak',cost_estimate=1000,currency='RUB',evidence_document_ids=[doc.id]),
        FieldQualityClaim(project_code=p.code,manufacturing_area='assembly',claim_reference='F2',vehicle_identifier='V2',part_number=part.part_number,supplier_code='SUP1',failure_mode='coolant leak',cost_estimate=500,currency='RUB',evidence_document_ids=[doc.id]),
    ]);db.commit()
    out=_ws(db,p,part,doc)
    assert out['field_feedback']['clusters'][0]['claims']==2
    assert out['copq']['by_currency'][0]['total']==2150.0
    assert out['copq']['erp_finance_system_of_record'] is True


def test_mixed_hidden_evidence_fails_closed_for_series_rows():
    db=_db();p,part,doc,*rest=_seed(db,'ACL57')
    hidden=Document(filename='hidden.pdf',stored_path='/tmp/h',sha256='b'*64,status=DocumentStatus.ready,part_number=part.part_number,revision='D',doc_type='spec',project_code=p.code,manufacturing_area='assembly',acl_groups=['secret']);db.add(hidden);db.commit();db.refresh(hidden)
    _obs(db,p,part,doc,evidence_document_ids=[doc.id,hidden.id],defect_quantity=99)
    rows=visible_series_rows(db,p.code,{doc.id},{part.part_number},'assembly',{'assembly'})
    assert rows['observations']==[]


def test_ask_series_intelligence_never_claims_root_cause():
    db=_db();p,part,doc,*rest=_seed(db,'ASK57')
    t=datetime.now(timezone.utc)-timedelta(days=4)
    for i,d in enumerate([1,1,9,12]): _obs(db,p,part,doc,defect_code='GAP',inspected_quantity=1000,defect_quantity=d,observed_at=t+timedelta(days=i))
    ws=_ws(db,p,part,doc); ans=series_intelligence_answer(ws,'Почему выросли дефекты?')
    assert ans['causal_claim'] is False and ans['human_investigation_required'] is True
    assert 'GAP' in ans['answer']
