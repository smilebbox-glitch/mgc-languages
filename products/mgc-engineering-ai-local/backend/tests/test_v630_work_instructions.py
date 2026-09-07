from __future__ import annotations
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db import models  # noqa
from app.db.models import Project, Document, ManufacturingLine, ProcessStation, ProcessOperation, WorkInstruction, ManufacturingLayout
from app.db.migrations import ensure_v630_schema
from app.services.engineering_translation import detect_language, validate_protected_tokens, _glossary_translation
from app.services.work_instructions import workspace, instruction_completeness


def _db():
    eng=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng)()


def test_v630_schema_marker_and_new_tables():
    eng,_=_db(); ensure_v630_schema(eng); ensure_v630_schema(eng)
    with eng.begin() as c:
        assert c.execute(text('SELECT schema_version FROM mgc_schema_state WHERE id=1')).scalar_one()=='6.3.0'
        names={r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert {'work_instructions','manufacturing_layouts','station_layout_placements','engineering_translation_memory'} <= names


def test_translation_language_and_engineering_token_guard():
    assert detect_language('螺栓')=='zh'; assert detect_language('Bracket')=='en'; assert detect_language('Кронштейн')=='ru'
    assert _glossary_translation('螺栓','ru')=='болт'
    source='Install PN-123 bracket, torque 25 Nm'
    assert validate_protected_tokens(source,'Установить PN-123 кронштейн, момент 25 Nm')==[]
    assert validate_protected_tokens(source,'Установить кронштейн')


def test_workspace_is_area_scoped_and_evidence_fail_closed():
    _,db=_db(); db.add(Project(code='P1',name='P1')); db.flush()
    la=ManufacturingLine(project_code='P1',manufacturing_area='assembly',code='A1',name='Assembly'); lw=ManufacturingLine(project_code='P1',manufacturing_area='welding',code='W1',name='Welding'); db.add_all([la,lw]); db.flush()
    sa=ProcessStation(line_id=la.id,code='ST10',name='Station 10',operator_role='Assembler',headcount=2); sw=ProcessStation(line_id=lw.id,code='ST20',name='Station 20'); db.add_all([sa,sw]); db.flush()
    da=Document(filename='visible.pdf',stored_path='/tmp/a',sha256='a'*64,project_code='P1',manufacturing_area='assembly'); dh=Document(filename='hidden.pdf',stored_path='/tmp/h',sha256='b'*64,project_code='P1',manufacturing_area='assembly'); db.add_all([da,dh]); db.flush()
    db.add_all([
        WorkInstruction(project_code='P1',manufacturing_area='assembly',station_id=sa.id,code='WI-A',title='Visible',source_document_id=da.id,steps_json=[{'sequence':10,'text':'Step'}]),
        WorkInstruction(project_code='P1',manufacturing_area='assembly',station_id=sa.id,code='WI-H',title='Hidden',source_document_id=dh.id,steps_json=[{'sequence':10,'text':'Hidden'}]),
        WorkInstruction(project_code='P1',manufacturing_area='welding',station_id=sw.id,code='WI-W',title='Weld',steps_json=[{'sequence':10,'text':'Weld'}]),
    ]); db.commit()
    out=workspace(db,'P1','assembly',{da.id})
    assert [x['code'] for x in out['lines']]==['A1']
    assert [x['code'] for x in out['stations']]==['ST10']
    assert [x['code'] for x in out['instructions']]==['WI-A']


def test_foreign_instruction_requires_translation_review_for_completeness():
    wi=WorkInstruction(project_code='P1',manufacturing_area='assembly',code='WI-CN',title='CN',station_id='S',source_language='zh',translation_status='draft',steps_json=[{'sequence':10,'text':'安装'}],safety_points_json=['PPE'],quality_points_json=['Check'],tools_json=['Tool'],ppe_json=['Gloves'],operator_role='Operator',cycle_time_sec=30)
    before=instruction_completeness(wi)
    assert 'foreign_translation_reviewed' in before['gaps']
    wi.translation_status='reviewed'
    after=instruction_completeness(wi)
    assert 'foreign_translation_reviewed' not in after['gaps']
