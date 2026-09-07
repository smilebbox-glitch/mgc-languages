from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    BuildGenealogyItem, DesignFMEAItem, Document, DocumentStatus, EngineeringRequirement,
    FieldQualityClaim, FieldReliabilityExposure, FieldServiceAction, Part, Project, ProjectArea,
    RequirementVerification, VehicleBuild,
)
from app.db.session import Base
from app.services.field_reliability_product_lifecycle import (
    field_intelligence_answer, field_reliability_workspace, vin_field_trace, visible_field_rows,
)


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db, code='F58'):
    p=Project(code=code,name='Field Reliability',acl_groups=['engineering-ai-users'])
    a=ProjectArea(project_code=code,code='components',name='Components',acl_groups=['engineering-ai-users'])
    part=Part(part_number=f'P-{code}',name='Pump',project_code=code,latest_revision='D',metadata_json={'manufacturing_area':'components'})
    doc=Document(filename='field.pdf',stored_path='/tmp/field.pdf',sha256='a'*64,status=DocumentStatus.ready,part_number=part.part_number,revision='D',doc_type='test',project_code=code,manufacturing_area='components',acl_groups=['engineering-ai-users'])
    db.add_all([p,a,part,doc]);db.commit();db.refresh(doc)
    return p,part,doc


def _claim(db,p,part,doc,ref,mileage=20000,rev='C',supplier='SUP1',severity='high',**kw):
    values=dict(project_code=p.code,manufacturing_area='components',claim_reference=ref,part_number=part.part_number,revision=rev,supplier_code=supplier,failure_mode='coolant leakage',failure_family='COOLANT LEAK',mileage_km=mileage,market='RU',climate_zone='temperate',severity=severity,status='open',claim_at=datetime.now(timezone.utc),evidence_document_ids=[doc.id],source_system='warranty')
    values.update(kw);row=FieldQualityClaim(**values);db.add(row);db.commit();db.refresh(row);return row


def _ws(db,p,part,doc,vin=None):
    return field_reliability_workspace(db,p.code,{doc.id},{part.part_number},'components',{'components'},vin)


def test_reliability_rate_and_weibull_use_censored_population():
    db=_db();p,part,doc=_seed(db,'WB58')
    db.add(FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',supplier_code='SUP1',market='RU',climate_zone='temperate',population_count=100,censored_count=96,censor_mileage_km=60000,total_exposure_km=4_500_000,evidence_document_ids=[doc.id]));db.commit()
    for i,m in enumerate([18000,24000,30000,36000]): _claim(db,p,part,doc,f'W{i}',mileage=m)
    r=_ws(db,p,part,doc)['reliability'][0]
    assert r['failure_rate_pct']==4.0 and r['failures_per_1000']==40.0
    assert r['weibull']['status']=='ESTIMATED' and r['weibull']['censored_count']==96
    assert r['weibull']['eta_km']>0 and r['weibull']['causal_claim'] is False


def test_weibull_refuses_insufficient_data():
    db=_db();p,part,doc=_seed(db,'INS58')
    db.add(FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',population_count=50,censored_count=49,censor_mileage_km=40000,evidence_document_ids=[doc.id]));db.commit()
    _claim(db,p,part,doc,'I1',mileage=15000,supplier=None)
    assert _ws(db,p,part,doc)['reliability'][0]['weibull']['status']=='INSUFFICIENT_DATA'


def test_failure_cluster_stays_investigation_only():
    db=_db();p,part,doc=_seed(db,'CL58')
    db.add(FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',supplier_code='SUP1',market='RU',climate_zone='hot',population_count=1000,censored_count=997,censor_mileage_km=50000,evidence_document_ids=[doc.id]));db.commit()
    for i in range(3): _claim(db,p,part,doc,f'C{i}',market='RU',climate_zone='hot',mileage=20000+i*1000)
    c=_ws(db,p,part,doc)['failure_clusters'][0]
    assert c['claims']==3 and c['supplier_code']=='SUP1' and c['climate_zone']=='hot'
    assert c['investigation_cluster'] is True and c['causal_claim'] is False


def test_dfmea_feedback_requires_human_review_when_field_occurrence_exceeds_assumption():
    db=_db();p,part,doc=_seed(db,'DF58')
    db.add_all([
        FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',population_count=500,censored_count=495,censor_mileage_km=50000,evidence_document_ids=[doc.id]),
        DesignFMEAItem(project_code=p.code,manufacturing_area='components',part_number=part.part_number,failure_mode='coolant leak',occurrence=1,severity=8,detection=4,evidence_document_ids=[doc.id]),
    ]);db.commit()
    for i in range(5): _claim(db,p,part,doc,f'D{i}',supplier=None,mileage=20000+i*500)
    row=_ws(db,p,part,doc)['dfmea_feedback'][0]
    assert row['status']=='DFMEA_REVIEW_REQUIRED' and row['human_dfmea_update_required'] is True


def test_validation_effectiveness_detects_field_failure_beyond_test_exposure():
    db=_db();p,part,doc=_seed(db,'VV58')
    req=EngineeringRequirement(project_code=p.code,manufacturing_area='components',code='RQ1',title='Coolant leak durability',requirement_text='No coolant leak',part_numbers=[part.part_number],source_document_id=doc.id)
    db.add(req);db.commit();db.refresh(req)
    vv=RequirementVerification(project_code=p.code,requirement_id=req.id,manufacturing_area='components',code='VV1',title='Pump durability',status='passed',phase='dv',measured_result_json={'validated_mileage_km':20000},evidence_document_ids=[doc.id])
    db.add_all([vv,FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',population_count=100,censored_count=98,censor_mileage_km=50000,evidence_document_ids=[doc.id])]);db.commit()
    _claim(db,p,part,doc,'V1',supplier=None,mileage=32000);_claim(db,p,part,doc,'V2',supplier=None,mileage=35000)
    gap=_ws(db,p,part,doc)['validation_effectiveness'][0]
    assert gap['status']=='VALIDATION_COVERAGE_GAP' and gap['validated_mileage_km']==20000
    assert gap['observed_failure_mileage_km']==32000


def test_revision_effectiveness_compares_field_rates_without_causal_claim():
    db=_db();p,part,doc=_seed(db,'REV58')
    db.add_all([
        FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',population_count=1000,censored_count=990,censor_mileage_km=50000,evidence_document_ids=[doc.id]),
        FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='D',population_count=1000,censored_count=998,censor_mileage_km=50000,evidence_document_ids=[doc.id]),
    ]);db.commit()
    for i in range(10): _claim(db,p,part,doc,f'RC{i}',rev='C',supplier=None,mileage=20000+i*100)
    for i in range(2): _claim(db,p,part,doc,f'RD{i}',rev='D',supplier=None,mileage=30000+i*100)
    e=_ws(db,p,part,doc)['revision_effectiveness'][0]
    assert e['best_observed_revision']=='D' and e['worst_observed_revision']=='C'
    assert e['positive_signal'] is True and e['causal_claim'] is False


def test_vin_field_trace_resolves_tsb_from_actual_genealogy():
    db=_db();p,part,doc=_seed(db,'VIN58')
    b=VehicleBuild(project_code=p.code,manufacturing_area='components',code='B1',vehicle_identifier='VIN100',plant='Kaluga',build_type='series_observation',status='completed',completed_at=datetime.now(timezone.utc),evidence_document_ids=[doc.id]);db.add(b);db.commit();db.refresh(b)
    db.add(BuildGenealogyItem(build_id=b.id,manufacturing_area='components',part_number=part.part_number,revision='C',supplier_code='SUP1',lot_number='L1',evidence_document_ids=[doc.id]));db.commit()
    db.add(FieldServiceAction(project_code=p.code,manufacturing_area='components',code='TSB1',action_type='tsb',title='Replace pump',status='active',part_number=part.part_number,revision='C',supplier_code='SUP1',repair='Install Rev D',evidence_document_ids=[doc.id]));db.commit()
    tr=vin_field_trace(db,p.code,'VIN100',{doc.id},{part.part_number},{'components'})
    assert tr['service_actions'][0]['vin_applicability']=='APPLICABLE'
    assert tr['genealogy'][0]['revision']=='C'


def test_repeat_repair_and_ntf_are_technical_patterns_not_dealer_rating():
    db=_db();p,part,doc=_seed(db,'REP58')
    _claim(db,p,part,doc,'R1',repair_method='replace seal',repeat_repair=True,no_trouble_found=False)
    _claim(db,p,part,doc,'R2',repair_method='replace seal',repeat_repair=False,no_trouble_found=True)
    row=_ws(db,p,part,doc)['repair_patterns'][0]
    assert row['repeat_repair_rate_pct']==50.0 and row['ntf_rate_pct']==50.0
    assert row['dealer_performance_rating'] is False


def test_campaign_candidate_is_advisory_and_never_recall_decision():
    db=_db();p,part,doc=_seed(db,'CAM58')
    db.add(FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',population_count=100,censored_count=96,censor_mileage_km=50000,evidence_document_ids=[doc.id]));db.commit()
    for i in range(4): _claim(db,p,part,doc,f'CAM{i}',supplier=None,severity='critical')
    c=_ws(db,p,part,doc)['campaign_candidates'][0]
    assert c['status']=='REVIEW_REQUIRED' and c['campaign_or_recall_decision'] is False
    assert 'Legal/Homologation' in c['required_authorities']


def test_mixed_hidden_evidence_fails_closed_for_field_exposure_and_action():
    db=_db();p,part,doc=_seed(db,'ACL58')
    hidden=Document(filename='secret.pdf',stored_path='/tmp/secret',sha256='b'*64,status=DocumentStatus.ready,part_number=part.part_number,project_code=p.code,manufacturing_area='components',acl_groups=['secret']);db.add(hidden);db.commit();db.refresh(hidden)
    db.add_all([
        FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,population_count=999,evidence_document_ids=[doc.id,hidden.id]),
        FieldServiceAction(project_code=p.code,manufacturing_area='components',code='S1',title='Secret action',part_number=part.part_number,evidence_document_ids=[doc.id,hidden.id]),
    ]);db.commit()
    rows=visible_field_rows(db,p.code,{doc.id},{part.part_number},'components',{'components'})
    assert rows['exposures']==[] and rows['actions']==[]


def test_field_intelligence_answer_never_claims_root_cause():
    db=_db();p,part,doc=_seed(db,'ASK58')
    db.add(FieldReliabilityExposure(project_code=p.code,manufacturing_area='components',part_number=part.part_number,revision='C',population_count=100,censored_count=97,censor_mileage_km=50000,evidence_document_ids=[doc.id]));db.commit()
    for i in range(3): _claim(db,p,part,doc,f'A{i}',supplier=None)
    ans=field_intelligence_answer(_ws(db,p,part,doc),'Почему отказывает насос?')
    assert ans['generated'] is False and ans['causal_claim'] is False and ans['human_investigation_required'] is True
