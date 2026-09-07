from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    ChangeRequest, Document, DocumentStatus, EngineeringWorkflowCase, Part, Project, ProjectArea, ProjectMilestone
)
from app.db.session import Base
from app.services.engineering_intelligence_os import (
    advance_workflow_case, initialize_workflow_state, operating_system_workspace, serialize_workflow, visible_workflow_cases
)


def _db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db, code='OS60'):
    p=Project(code=code,name='Engineering OS',acl_groups=['engineering-ai-users'],phase='launch')
    a=ProjectArea(project_code=code,code='assembly',name='Assembly',acl_groups=['engineering-ai-users'])
    part=Part(part_number=f'P-{code}',name='Bracket',project_code=code,latest_revision='B')
    doc=Document(filename='drawing.pdf',stored_path='/tmp/drawing.pdf',sha256='a'*64,status=DocumentStatus.ready,
                 project_code=code,part_number=part.part_number,revision='B',doc_type='drawing',manufacturing_area='assembly',
                 acl_groups=['engineering-ai-users'])
    db.add_all([p,a,part,doc]);db.commit();db.refresh(doc)
    return p,part,doc


def _ws(db,p,part,doc,role='engineering'):
    return operating_system_workspace(db,p,{doc.id},{part.part_number},None,{'assembly'},'alice',role)


def test_role_changes_focus_but_not_authorization_scope():
    db=_db();p,part,doc=_seed(db,'ROLE60')
    eng=_ws(db,p,part,doc,'engineering')
    mfg=_ws(db,p,part,doc,'manufacturing')
    assert eng['governance']['role_is_ui_focus_not_authorization'] is True
    assert 'field' not in eng['cockpit']['domains']
    assert 'field' not in mfg['cockpit']['domains']
    assert set(eng['cockpit']['all_domains'])==set(mfg['cockpit']['all_domains'])
    assert eng['role']['code']=='engineering' and mfg['role']['code']=='manufacturing'


def test_unified_inbox_aggregates_high_risk_change_and_trace_gap():
    db=_db();p,part,doc=_seed(db,'ACT60')
    c=ChangeRequest(code='ECR-1',part_number=part.part_number,from_revision='A',to_revision='B',title='Supplier bracket change',
                    description='test',risk_level='high',status='draft',affected_document_ids=[doc.id],affected_parts=[part.part_number],created_by='alice')
    db.add(c);db.commit()
    ws=_ws(db,p,part,doc)
    titles=[x['title'] for x in ws['action_inbox']['focused']]
    assert any('ECR-1' in x for x in titles)
    assert any('3D/CAD' in x for x in titles)
    assert ws['action_inbox']['counts']['high']>=1


def test_workflow_progress_is_deterministic_and_human_closed():
    db=_db();p,part,doc=_seed(db,'WF60')
    state=initialize_workflow_state('defect_to_change')
    row=EngineeringWorkflowCase(project_code=p.code,manufacturing_area='assembly',code='WF-1',workflow_type='defect_to_change',
                                title='Bracket crack',status='active',priority='high',owner='alice',current_stage='contain',
                                workflow_state_json=state,evidence_document_ids=[doc.id],created_by='alice')
    db.add(row);db.commit();db.refresh(row)
    advance_workflow_case(row,complete_current_stage=True);db.commit();db.refresh(row)
    out=serialize_workflow(row)
    assert out['current_stage']=='root_cause'
    assert out['progress_pct']==20.0
    assert out['human_approval_required'] is True
    for _ in range(4): advance_workflow_case(row,complete_current_stage=True)
    db.commit();db.refresh(row)
    assert row.status=='ready_for_close'


def test_blocked_workflow_appears_as_decision_required_action():
    db=_db();p,part,doc=_seed(db,'BLK60')
    row=EngineeringWorkflowCase(project_code=p.code,manufacturing_area='assembly',code='WF-B',workflow_type='launch_blocker',title='PPAP blocker',
                                status='active',priority='critical',owner='alice',current_stage='triage',workflow_state_json=initialize_workflow_state('launch_blocker'),
                                due_at=datetime.now(timezone.utc)-timedelta(days=1),evidence_document_ids=[doc.id],created_by='alice')
    db.add(row);db.commit();db.refresh(row)
    advance_workflow_case(row,block_reason='PPAP evidence missing');db.commit()
    ws=_ws(db,p,part,doc,'program')
    wf=[x for x in ws['action_inbox']['focused'] if x['source_type']=='workflow'][0]
    assert wf['priority']=='critical' and wf['decision_required'] is True
    assert ws['action_inbox']['counts']['mine']>=1


def test_mixed_hidden_workflow_evidence_fails_closed():
    db=_db();p,part,doc=_seed(db,'ACL60')
    hidden=Document(filename='secret.pdf',stored_path='/tmp/secret.pdf',sha256='b'*64,status=DocumentStatus.ready,
                    project_code=p.code,part_number=part.part_number,revision='B',doc_type='test',manufacturing_area='assembly',acl_groups=['secret'])
    db.add(hidden);db.commit();db.refresh(hidden)
    visible=EngineeringWorkflowCase(project_code=p.code,code='WF-V',workflow_type='change_to_release',title='Visible',status='active',priority='normal',owner='alice',
                                    current_stage='impact',workflow_state_json=initialize_workflow_state('change_to_release'),evidence_document_ids=[doc.id],created_by='alice')
    mixed=EngineeringWorkflowCase(project_code=p.code,code='WF-H',workflow_type='change_to_release',title='Hidden mixed',status='active',priority='critical',owner='alice',
                                  current_stage='impact',workflow_state_json=initialize_workflow_state('change_to_release'),evidence_document_ids=[doc.id,hidden.id],created_by='alice')
    db.add_all([visible,mixed]);db.commit()
    rows=visible_workflow_cases(db,p.code,{doc.id},None,{'assembly'})
    assert {x.code for x in rows}=={'WF-V'}
    ws=_ws(db,p,part,doc,'engineering_admin')
    assert {x['code'] for x in ws['workflows']}=={'WF-V'}
    assert all('Hidden mixed' not in x['title'] for x in ws['action_inbox']['all_accessible'])


def test_program_gate_context_is_visible_in_cockpit():
    db=_db();p,part,doc=_seed(db,'GATE60')
    m=ProjectMilestone(project_code=p.code,code='SOP',name='SOP',gate='sop',status='planned',due_at=datetime.now(timezone.utc)-timedelta(days=1),owner='alice')
    db.add(m);db.commit()
    ws=_ws(db,p,part,doc,'program')
    assert ws['cockpit']['next_gate']['code']=='SOP'
    assert ws['cockpit']['program_forecast']['band'] in {'AMBER','RED'}
    assert ws['command_brief']['generated'] is False
