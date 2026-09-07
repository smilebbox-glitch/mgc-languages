from datetime import datetime
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)
    part_number: str | None = None
    revision: str | None = None
    doc_type: str | None = None
    project_code: str | None = None
    manufacturing_area: str | None = None


class SearchHit(BaseModel):
    score: float
    document_id: str
    filename: str
    chunk_index: int
    text: str
    page: int | None = None
    part_number: str | None = None
    revision: str | None = None
    doc_type: str | None = None
    project_code: str | None = None
    manufacturing_area: str | None = None
    metadata: dict = {}


class AskRequest(SearchRequest):
    conversation: list[dict] = []


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchHit]
    generated: bool
    query_plan: dict = {}
    confidence: str = "unknown"


class IssueUpdate(BaseModel):
    status: str

class DesignReviewRequest(BaseModel):
    part_number: str
    revision: str
    baseline_revision: str | None = None


class ImpactRequest(BaseModel):
    part_number: str
    from_revision: str
    to_revision: str
    max_depth: int = Field(default=4, ge=1, le=8)


class EvidencePackRequest(BaseModel):
    part_number: str
    revision: str | None = None
    pack_type: str = "engineering"


class AgentRequest(BaseModel):
    instruction: str


class ApprovalRequest(BaseModel):
    decision: str
    comment: str | None = None


class ExternalSystemCreate(BaseModel):
    code: str
    name: str
    connector_type: str
    config: dict = {}
    secrets: dict = {}
    acl_groups: list[str] = ["all"]
    enabled: bool = True
    source_domain: str | None = Field(default=None, pattern="^(engineering|plm|pdm|erp|mes|qms|cad|files)$")
    contract_version: str = Field(default="mgc-integration-v1", pattern="^mgc-integration-v1$")
    expected_freshness_minutes: int | None = Field(default=None, ge=1, le=525600)
    required_fields: list[str] = []


class ExternalSystemUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    secrets: dict | None = None
    acl_groups: list[str] | None = None
    enabled: bool | None = None
    source_domain: str | None = Field(default=None, pattern="^(engineering|plm|pdm|erp|mes|qms|cad|files)$")
    contract_version: str | None = Field(default=None, pattern="^mgc-integration-v1$")
    expected_freshness_minutes: int | None = Field(default=None, ge=1, le=525600)
    required_fields: list[str] | None = None


class IntegrationEntityMappingCreate(BaseModel):
    system_id: str = Field(min_length=1, max_length=36)
    project_code: str = Field(min_length=1, max_length=64)
    source_entity_type: str = Field(pattern="^(part|vin|supplier|bom_position|defect)$")
    source_external_id: str = Field(min_length=1, max_length=512)
    source_key: str | None = Field(default=None, max_length=512)
    canonical_entity_type: str = Field(pattern="^(part|vin|supplier|bom_position|defect)$")
    canonical_key: str = Field(min_length=1, max_length=512)
    notes: str | None = Field(default=None, max_length=3000)


class IntegrationEntityMappingUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(confirmed|rejected|retired)$")
    canonical_key: str | None = Field(default=None, min_length=1, max_length=512)
    notes: str | None = Field(default=None, max_length=3000)
    reverify: bool = False


class IntegrationReconciliationRequest(BaseModel):
    project_code: str = Field(min_length=1, max_length=64)
    required_roles: list[str] | None = None
    min_mapping_coverage: float = Field(default=0.95, ge=0, le=1)
    min_freshness_compliance: float = Field(default=0.95, ge=0, le=1)
    min_sync_success_rate: float = Field(default=0.95, ge=0, le=1)


class IntegrationCertificationRequest(BaseModel):
    live_probe: bool = True
    sample_limit: int = Field(default=20, ge=1, le=50)


class IntegrationSyncRequest(BaseModel):
    reset_cursor: bool = False
    page_limit: int = Field(default=100, ge=1, le=1000)
    max_pages: int = Field(default=20, ge=1, le=1000)


class CadConvertRequest(BaseModel):
    document_id: str
    gateway_system_code: str | None = None
    target_format: str = "auto"


class DocumentActivityNoteRequest(BaseModel):
    summary: str = Field(min_length=2, max_length=1000)
    category: str = Field(default="work_done", pattern="^(work_done|review|decision|question|other)$")
    details: dict = {}

class ChangeCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=512)
    description: str | None = Field(default=None, max_length=5000)
    reason: str = Field(min_length=3, max_length=3000)
    part_number: str = Field(min_length=1, max_length=128)
    from_revision: str = Field(min_length=1, max_length=64)
    to_revision: str = Field(min_length=1, max_length=64)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")


class ChangeDecisionRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    stage: str = Field(pattern="^(technical_review|final_approval)$")
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str | None = Field(default=None, max_length=3000)


class ChangeImplementationRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    implementation_plan: dict = {}
    verification_plan: dict = {}


class ChangeCompleteRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    verification_result: str = Field(min_length=3, max_length=5000)

class ProjectCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    phase: str = Field(default="development", max_length=64)
    owner: str | None = Field(default=None, max_length=255)
    root_part_number: str | None = Field(default=None, max_length=128)
    target_release_at: str | None = None
    acl_groups: list[str] = []


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, pattern="^(active|on_hold|completed|archived)$")
    phase: str | None = Field(default=None, max_length=64)
    owner: str | None = Field(default=None, max_length=255)
    root_part_number: str | None = Field(default=None, max_length=128)
    target_release_at: str | None = None
    acl_groups: list[str] | None = None


class MilestoneCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    due_at: str | None = None
    owner: str | None = Field(default=None, max_length=255)
    gate: str = Field(default="engineering", max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=3000)


class MilestoneUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    due_at: str | None = None
    status: str | None = Field(default=None, pattern="^(planned|in_progress|blocked|done|waived)$")
    owner: str | None = Field(default=None, max_length=255)
    gate: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=3000)


class ProjectAreaUpdateRequest(BaseModel):
    owner: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    acl_groups: list[str] | None = None
    notes: str | None = Field(default=None, max_length=3000)


class DocumentAreaUpdateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)


class APQPDeliverableCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    phase: str = Field(default="planning", max_length=64)
    title: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    owner: str | None = Field(default=None, max_length=255)
    due_at: str | None = None
    linked_part_numbers: list[str] = []
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=3000)


class APQPDeliverableUpdateRequest(BaseModel):
    phase: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    owner: str | None = Field(default=None, max_length=255)
    due_at: str | None = None
    status: str | None = Field(default=None, pattern="^(planned|in_progress|blocked|done|waived)$")
    linked_part_numbers: list[str] | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=3000)


class SpecialCharacteristicCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    category: str = Field(default="critical", pattern="^(safety|regulatory|critical|significant|customer|other)$")
    symbol: str | None = Field(default=None, max_length=64)
    description: str = Field(min_length=2, max_length=1024)
    specification: str | None = Field(default=None, max_length=1024)
    unit: str | None = Field(default=None, max_length=64)
    source_document_id: str | None = None
    source_reference: dict = {}
    owner: str | None = Field(default=None, max_length=255)


class SpecialCharacteristicUpdateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, pattern="^(safety|regulatory|critical|significant|customer|other)$")
    symbol: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, min_length=2, max_length=1024)
    specification: str | None = Field(default=None, max_length=1024)
    unit: str | None = Field(default=None, max_length=64)
    source_document_id: str | None = None
    source_reference: dict | None = None
    owner: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(open|controlled|verified|retired)$")


class PFMEAItemCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    process_step: str = Field(min_length=2, max_length=512)
    process_operation_id: str | None = None
    function: str | None = Field(default=None, max_length=3000)
    failure_mode: str = Field(min_length=2, max_length=3000)
    effect: str | None = Field(default=None, max_length=3000)
    cause: str | None = Field(default=None, max_length=3000)
    prevention_control: str | None = Field(default=None, max_length=3000)
    detection_control: str | None = Field(default=None, max_length=3000)
    severity: int = Field(default=1, ge=1, le=10)
    occurrence: int = Field(default=1, ge=1, le=10)
    detection: int = Field(default=1, ge=1, le=10)
    action_priority: str | None = Field(default=None, pattern="^(H|M|L|h|m|l)$")
    recommended_action: str | None = Field(default=None, max_length=3000)
    action_owner: str | None = Field(default=None, max_length=255)
    due_at: str | None = None
    special_characteristic_ids: list[str] = []
    evidence_document_ids: list[str] = []


class PFMEAItemUpdateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    process_step: str | None = Field(default=None, min_length=2, max_length=512)
    process_operation_id: str | None = None
    function: str | None = Field(default=None, max_length=3000)
    failure_mode: str | None = Field(default=None, min_length=2, max_length=3000)
    effect: str | None = Field(default=None, max_length=3000)
    cause: str | None = Field(default=None, max_length=3000)
    prevention_control: str | None = Field(default=None, max_length=3000)
    detection_control: str | None = Field(default=None, max_length=3000)
    severity: int | None = Field(default=None, ge=1, le=10)
    occurrence: int | None = Field(default=None, ge=1, le=10)
    detection: int | None = Field(default=None, ge=1, le=10)
    action_priority: str | None = Field(default=None, pattern="^(H|M|L|h|m|l)$")
    recommended_action: str | None = Field(default=None, max_length=3000)
    action_owner: str | None = Field(default=None, max_length=255)
    due_at: str | None = None
    status: str | None = Field(default=None, pattern="^(open|action|controlled|closed)$")
    special_characteristic_ids: list[str] | None = None
    evidence_document_ids: list[str] | None = None


class ControlPlanItemCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    process_step: str = Field(min_length=2, max_length=512)
    process_operation_id: str | None = None
    characteristic_id: str | None = None
    characteristic: str = Field(min_length=2, max_length=1024)
    specification: str | None = Field(default=None, max_length=1024)
    measurement_method: str | None = Field(default=None, max_length=1024)
    sample_size: str | None = Field(default=None, max_length=128)
    frequency: str | None = Field(default=None, max_length=255)
    reaction_plan: str | None = Field(default=None, max_length=3000)
    control_phase: str = Field(default="production", pattern="^(prototype|pre_launch|production|safe_launch)$")
    owner: str | None = Field(default=None, max_length=255)
    status: str = Field(default="draft", pattern="^(draft|active|verified|retired)$")
    evidence_document_ids: list[str] = []


class ControlPlanItemUpdateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    process_step: str | None = Field(default=None, min_length=2, max_length=512)
    process_operation_id: str | None = None
    characteristic_id: str | None = None
    characteristic: str | None = Field(default=None, min_length=2, max_length=1024)
    specification: str | None = Field(default=None, max_length=1024)
    measurement_method: str | None = Field(default=None, max_length=1024)
    sample_size: str | None = Field(default=None, max_length=128)
    frequency: str | None = Field(default=None, max_length=255)
    reaction_plan: str | None = Field(default=None, max_length=3000)
    control_phase: str | None = Field(default=None, pattern="^(prototype|pre_launch|production|safe_launch)$")
    owner: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(draft|active|verified|retired)$")
    evidence_document_ids: list[str] | None = None


class PPAPCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_name: str | None = Field(default=None, max_length=512)
    customer: str | None = Field(default=None, max_length=255)
    submission_level: str | None = Field(default=None, max_length=32)
    due_at: str | None = None
    element_status: dict = {}
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=3000)


class PPAPUpdateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_name: str | None = Field(default=None, max_length=512)
    customer: str | None = Field(default=None, max_length=255)
    submission_level: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, pattern="^(draft|preparing|submitted|approved|rejected|expired)$")
    due_at: str | None = None
    element_status: dict | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=3000)


class Problem8DCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    complaint_reference: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=2, max_length=512)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    owner: str | None = Field(default=None, max_length=255)
    team: list = []
    linked_change_id: str | None = None
    evidence_document_ids: list[str] = []


class Problem8DUpdateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    complaint_reference: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, min_length=2, max_length=512)
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    status: str | None = Field(default=None, pattern="^(open|containment|root_cause|corrective_action|verification|closed|cancelled)$")
    owner: str | None = Field(default=None, max_length=255)
    team: list | None = None
    disciplines: dict | None = None
    linked_change_id: str | None = None
    evidence_document_ids: list[str] | None = None


class ManufacturingLineCreateRequest(BaseModel):
    manufacturing_area: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    plant: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=255)


class ProcessStationCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    sequence: int = Field(default=100, ge=0, le=100000)
    owner: str | None = Field(default=None, max_length=255)
    operator_role: str | None = Field(default=None, max_length=255)
    headcount: int = Field(default=1, ge=1, le=100)
    work_content: str | None = Field(default=None, max_length=5000)
    takt_time_sec: float | None = Field(default=None, ge=0, le=86400)


class ProcessStationUpdateRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    sequence: int | None = Field(default=None, ge=0, le=100000)
    owner: str | None = Field(default=None, max_length=255)
    operator_role: str | None = Field(default=None, max_length=255)
    headcount: int | None = Field(default=None, ge=1, le=100)
    work_content: str | None = Field(default=None, max_length=5000)
    takt_time_sec: float | None = Field(default=None, ge=0, le=86400)
    status: str | None = Field(default=None, pattern="^(active|inactive|planned)$")


class ProcessOperationCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    sequence: int = Field(default=100, ge=0, le=100000)
    operation_type: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    cycle_time_sec: float | None = Field(default=None, ge=0, le=86400)
    work_instruction_document_ids: list[str] = []
    owner: str | None = Field(default=None, max_length=255)


class ProcessAssetCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    asset_type: str = Field(default="equipment", pattern="^(equipment|fixture|tool|gauge|measurement|robot|conveyor|other)$")
    asset_reference: str | None = Field(default=None, max_length=255)
    calibration_due_at: str | None = None
    maintenance_due_at: str | None = None


class ProcessParameterCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    target_value: float | None = None
    lower_spec_limit: float | None = None
    upper_spec_limit: float | None = None
    unit: str | None = Field(default=None, max_length=64)
    special_characteristic_id: str | None = None
    control_plan_item_id: str | None = None
    measurement_method: str | None = Field(default=None, max_length=1024)
    reaction_plan: str | None = Field(default=None, max_length=3000)


class ProcessDefectCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    line_id: str | None = None
    station_id: str | None = None
    operation_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    defect_code: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=2, max_length=512)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    quantity: int = Field(default=1, ge=1, le=100000000)
    linked_8d_id: str | None = None
    evidence_document_ids: list[str] = []
    occurred_at: str | None = None


class ProcessDefectUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|contained|investigating|resolved|closed|cancelled)$")
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    linked_8d_id: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=100000000)



class LaunchReadinessItemCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    category: str = Field(pattern="^(tooling|equipment|supplier|capacity|pilot_build|validation|packaging|logistics|staffing|training|safe_launch|other)$")
    title: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    line_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    required: bool = True
    owner: str | None = Field(default=None, max_length=255)
    due_at: str | None = None
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_name: str | None = Field(default=None, max_length=512)
    criteria: dict = {}
    result: dict = {}
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=3000)


class LaunchReadinessItemUpdateRequest(BaseModel):
    category: str | None = Field(default=None, pattern="^(tooling|equipment|supplier|capacity|pilot_build|validation|packaging|logistics|staffing|training|safe_launch|other)$")
    title: str | None = Field(default=None, min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    line_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    required: bool | None = None
    status: str | None = Field(default=None, pattern="^(planned|in_progress|blocked|ready|waived|failed)$")
    owner: str | None = Field(default=None, max_length=255)
    due_at: str | None = None
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_name: str | None = Field(default=None, max_length=512)
    criteria: dict | None = None
    result: dict | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=3000)


class LaunchTrialCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    trial_type: str = Field(pattern="^(run_at_rate|pilot_build|dv|pv|safe_launch|other)$")
    title: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    line_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    owner: str | None = Field(default=None, max_length=255)
    planned_at: str | None = None
    planned_quantity: int | None = Field(default=None, ge=0, le=100000000)
    target_rate_per_hour: float | None = Field(default=None, ge=0)
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=3000)


class LaunchTrialUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=512)
    status: str | None = Field(default=None, pattern="^(planned|in_progress|passed|failed|cancelled)$")
    owner: str | None = Field(default=None, max_length=255)
    planned_at: str | None = None
    completed_at: str | None = None
    planned_quantity: int | None = Field(default=None, ge=0, le=100000000)
    produced_quantity: int | None = Field(default=None, ge=0, le=100000000)
    good_quantity: int | None = Field(default=None, ge=0, le=100000000)
    target_rate_per_hour: float | None = Field(default=None, ge=0)
    actual_rate_per_hour: float | None = Field(default=None, ge=0)
    duration_minutes: float | None = Field(default=None, ge=0)
    result: dict | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=3000)


class EngineeringRequirementCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._/-]+$")
    category: str = Field(default="oem", pattern="^(oem|regulatory|legal|customer|system|interface|manufacturing|quality|internal|other)$")
    criticality: str = Field(default="normal", pattern="^(normal|important|critical|safety|regulatory)$")
    title: str = Field(min_length=2, max_length=512)
    requirement_text: str = Field(min_length=2, max_length=12000)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    source_document_id: str | None = None
    source_reference: dict = {}
    system_name: str | None = Field(default=None, max_length=255)
    function_name: str | None = Field(default=None, max_length=512)
    part_numbers: list[str] = []
    special_characteristic_ids: list[str] = []
    verification_method: str | None = Field(default=None, pattern="^(analysis|inspection|test|review|demonstration|simulation|measurement|other)$")
    acceptance_criteria: str | None = Field(default=None, max_length=5000)
    linked_change_ids: list[str] = []
    owner: str | None = Field(default=None, max_length=255)


class EngineeringRequirementUpdateRequest(BaseModel):
    category: str | None = Field(default=None, pattern="^(oem|regulatory|legal|customer|system|interface|manufacturing|quality|internal|other)$")
    criticality: str | None = Field(default=None, pattern="^(normal|important|critical|safety|regulatory)$")
    title: str | None = Field(default=None, min_length=2, max_length=512)
    requirement_text: str | None = Field(default=None, min_length=2, max_length=12000)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    source_document_id: str | None = None
    source_reference: dict | None = None
    system_name: str | None = Field(default=None, max_length=255)
    function_name: str | None = Field(default=None, max_length=512)
    part_numbers: list[str] | None = None
    special_characteristic_ids: list[str] | None = None
    verification_method: str | None = Field(default=None, pattern="^(analysis|inspection|test|review|demonstration|simulation|measurement|other)$")
    acceptance_criteria: str | None = Field(default=None, max_length=5000)
    linked_change_ids: list[str] | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|waived|retired)$")
    owner: str | None = Field(default=None, max_length=255)


class RequirementVerificationCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._/-]+$")
    verification_type: str = Field(default="test", pattern="^(analysis|inspection|test|review|demonstration|simulation|measurement|other)$")
    phase: str = Field(default="dv", pattern="^(concept|prototype|dv|pv|pre_launch|production|other)$")
    title: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    status: str = Field(default="planned", pattern="^(planned|in_progress|passed|failed|blocked|waived)$")
    result_summary: str | None = Field(default=None, max_length=5000)
    measured_result: dict = {}
    evidence_document_ids: list[str] = []
    launch_trial_id: str | None = None
    design_review_id: str | None = None
    linked_change_id: str | None = None
    notes: str | None = Field(default=None, max_length=3000)


class RequirementVerificationUpdateRequest(BaseModel):
    verification_type: str | None = Field(default=None, pattern="^(analysis|inspection|test|review|demonstration|simulation|measurement|other)$")
    phase: str | None = Field(default=None, pattern="^(concept|prototype|dv|pv|pre_launch|production|other)$")
    title: str | None = Field(default=None, min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, pattern="^(planned|in_progress|passed|failed|blocked|waived)$")
    result_summary: str | None = Field(default=None, max_length=5000)
    measured_result: dict | None = None
    evidence_document_ids: list[str] | None = None
    launch_trial_id: str | None = None
    design_review_id: str | None = None
    linked_change_id: str | None = None
    notes: str | None = Field(default=None, max_length=3000)


class LocalizationItemCreateRequest(BaseModel):
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._/-]+$")
    supplier_name: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    source_country: str | None = Field(default=None, max_length=128)
    local_plant: str | None = Field(default=None, max_length=255)
    status: str = Field(default="candidate", pattern="^(candidate|rfq|nominated|tooling|validation|approved|sop|hold|cancelled)$")
    localization_percent: float | None = Field(default=None, ge=0, le=100)
    target_localization_percent: float | None = Field(default=None, ge=0, le=100)
    technical_package_status: str = Field(default="missing", pattern="^(missing|in_progress|ready|waived)$")
    rfq_status: str = Field(default="planned", pattern="^(planned|sent|received|complete|waived)$")
    nomination_status: str = Field(default="planned", pattern="^(planned|approved|rejected|waived)$")
    tooling_status: str = Field(default="planned", pattern="^(not_required|planned|in_progress|ready|failed|waived)$")
    capacity_status: str = Field(default="planned", pattern="^(planned|in_progress|confirmed|failed|waived)$")
    owner: str | None = Field(default=None, max_length=255)
    planned_sop_at: str | None = None
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class LocalizationItemUpdateRequest(BaseModel):
    revision: str | None = Field(default=None, max_length=64)
    supplier_name: str | None = Field(default=None, min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    source_country: str | None = Field(default=None, max_length=128)
    local_plant: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(candidate|rfq|nominated|tooling|validation|approved|sop|hold|cancelled)$")
    localization_percent: float | None = Field(default=None, ge=0, le=100)
    target_localization_percent: float | None = Field(default=None, ge=0, le=100)
    technical_package_status: str | None = Field(default=None, pattern="^(missing|in_progress|ready|waived)$")
    rfq_status: str | None = Field(default=None, pattern="^(planned|sent|received|complete|waived)$")
    nomination_status: str | None = Field(default=None, pattern="^(planned|approved|rejected|waived)$")
    tooling_status: str | None = Field(default=None, pattern="^(not_required|planned|in_progress|ready|failed|waived)$")
    capacity_status: str | None = Field(default=None, pattern="^(planned|in_progress|confirmed|failed|waived)$")
    owner: str | None = Field(default=None, max_length=255)
    planned_sop_at: str | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


class IncomingQualityCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._/-]+$")
    supplier_code: str = Field(min_length=1, max_length=128)
    supplier_name: str | None = Field(default=None, max_length=512)
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    lot_reference: str | None = Field(default=None, max_length=255)
    inspection_type: str = Field(default="incoming", pattern="^(incoming|dock_audit|containment|safe_launch|sorting|other)$")
    inspected_quantity: int = Field(default=0, ge=0, le=100000000)
    rejected_quantity: int = Field(default=0, ge=0, le=100000000)
    defect_quantity: int = Field(default=0, ge=0, le=100000000)
    defect_code: str | None = Field(default=None, max_length=64)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    status: str = Field(default="open", pattern="^(open|contained|investigating|resolved|closed|cancelled)$")
    acceptance_limit_pct: float | None = Field(default=None, ge=0, le=100)
    linked_8d_id: str | None = None
    evidence_document_ids: list[str] = []
    occurred_at: str | None = None
    notes: str | None = Field(default=None, max_length=5000)


class IncomingQualityUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|contained|investigating|resolved|closed|cancelled)$")
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    inspected_quantity: int | None = Field(default=None, ge=0, le=100000000)
    rejected_quantity: int | None = Field(default=None, ge=0, le=100000000)
    defect_quantity: int | None = Field(default=None, ge=0, le=100000000)
    acceptance_limit_pct: float | None = Field(default=None, ge=0, le=100)
    linked_8d_id: str | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


class CostBaselineCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._/-]+$")
    name: str = Field(min_length=2, max_length=255)
    baseline_type: str = Field(default="current", pattern="^(current|target|change|localization|scenario)$")
    status: str = Field(default="draft", pattern="^(draft|active|frozen|archived)$")
    currency: str = Field(default="RUB", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    annual_volume: int | None = Field(default=None, ge=1, le=100000000)
    target_vehicle_cost: float | None = Field(default=None, ge=0)
    reference_baseline_id: str | None = None
    linked_change_id: str | None = None
    effective_at: str | None = None
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class CostBaselineUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    baseline_type: str | None = Field(default=None, pattern="^(current|target|change|localization|scenario)$")
    status: str | None = Field(default=None, pattern="^(draft|active|frozen|archived)$")
    currency: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    annual_volume: int | None = Field(default=None, ge=1, le=100000000)
    target_vehicle_cost: float | None = Field(default=None, ge=0)
    reference_baseline_id: str | None = None
    linked_change_id: str | None = None
    effective_at: str | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


class CostLineCreateRequest(BaseModel):
    baseline_id: str
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_name: str | None = Field(default=None, max_length=512)
    quantity_per_vehicle: float = Field(default=1.0, ge=0, le=100000)
    calculation_mode: str = Field(default="breakdown", pattern="^(breakdown|quote)$")
    mass_kg: float | None = Field(default=None, ge=0)
    material_name: str | None = Field(default=None, max_length=255)
    material_price_per_kg: float | None = Field(default=None, ge=0)
    scrap_rate_pct: float | None = Field(default=None, ge=0, le=1000)
    conversion_cost: float | None = Field(default=None, ge=0)
    logistics_cost: float | None = Field(default=None, ge=0)
    packaging_cost: float | None = Field(default=None, ge=0)
    overhead_cost: float | None = Field(default=None, ge=0)
    supplier_unit_price: float | None = Field(default=None, ge=0)
    other_unit_cost: float | None = Field(default=None, ge=0)
    tooling_cost: float | None = Field(default=None, ge=0)
    tooling_amortization_volume: int | None = Field(default=None, ge=1, le=1000000000)
    target_unit_cost: float | None = Field(default=None, ge=0)
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class CostLineUpdateRequest(BaseModel):
    revision: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_name: str | None = Field(default=None, max_length=512)
    quantity_per_vehicle: float | None = Field(default=None, ge=0, le=100000)
    calculation_mode: str | None = Field(default=None, pattern="^(breakdown|quote)$")
    mass_kg: float | None = Field(default=None, ge=0)
    material_name: str | None = Field(default=None, max_length=255)
    material_price_per_kg: float | None = Field(default=None, ge=0)
    scrap_rate_pct: float | None = Field(default=None, ge=0, le=1000)
    conversion_cost: float | None = Field(default=None, ge=0)
    logistics_cost: float | None = Field(default=None, ge=0)
    packaging_cost: float | None = Field(default=None, ge=0)
    overhead_cost: float | None = Field(default=None, ge=0)
    supplier_unit_price: float | None = Field(default=None, ge=0)
    other_unit_cost: float | None = Field(default=None, ge=0)
    tooling_cost: float | None = Field(default=None, ge=0)
    tooling_amortization_volume: int | None = Field(default=None, ge=1, le=1000000000)
    target_unit_cost: float | None = Field(default=None, ge=0)
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


class SupplierQuotationCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._/-]+$")
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str = Field(min_length=1, max_length=128)
    supplier_name: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    currency: str = Field(default="RUB", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    unit_price: float = Field(ge=0)
    tooling_cost: float | None = Field(default=None, ge=0)
    annual_volume: int | None = Field(default=None, ge=1, le=100000000)
    status: str = Field(default="received", pattern="^(draft|received|selected|rejected|expired)$")
    valid_until: str | None = None
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class SupplierQuotationUpdateRequest(BaseModel):
    revision: str | None = Field(default=None, max_length=64)
    supplier_name: str | None = Field(default=None, min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    unit_price: float | None = Field(default=None, ge=0)
    tooling_cost: float | None = Field(default=None, ge=0)
    annual_volume: int | None = Field(default=None, ge=1, le=100000000)
    status: str | None = Field(default=None, pattern="^(draft|received|selected|rejected|expired)$")
    valid_until: str | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


class ArchitectureNodeCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    name: str = Field(min_length=2, max_length=512)
    node_type: str = Field(default="component", pattern="^(vehicle|system|subsystem|assembly|component)$")
    parent_node_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    status: str = Field(default="active", pattern="^(draft|active|released|obsolete)$")
    owner: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    evidence_document_ids: list[str] = []

class ArchitectureNodeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=512)
    node_type: str | None = Field(default=None, pattern="^(vehicle|system|subsystem|assembly|component)$")
    parent_node_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, pattern="^(draft|active|released|obsolete)$")
    owner: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    evidence_document_ids: list[str] | None = None

class InterfaceCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    name: str = Field(min_length=2, max_length=512)
    interface_type: str = Field(default="mechanical", pattern="^(mechanical|electrical|fluid|thermal|data|control|packaging|other)$")
    source_node_id: str
    target_node_id: str
    manufacturing_area: str | None = Field(default=None, max_length=64)
    criticality: str = Field(default="normal", pattern="^(normal|high|critical|safety|regulatory)$")
    status: str = Field(default="active", pattern="^(draft|active|released|obsolete)$")
    owner: str | None = Field(default=None, max_length=255)
    requirement_ids: list[str] = []
    linked_change_ids: list[str] = []
    specifications: dict = {}
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)

class InterfaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=512)
    interface_type: str | None = Field(default=None, pattern="^(mechanical|electrical|fluid|thermal|data|control|packaging|other)$")
    source_node_id: str | None = None
    target_node_id: str | None = None
    manufacturing_area: str | None = Field(default=None, max_length=64)
    criticality: str | None = Field(default=None, pattern="^(normal|high|critical|safety|regulatory)$")
    status: str | None = Field(default=None, pattern="^(draft|active|released|obsolete)$")
    owner: str | None = Field(default=None, max_length=255)
    requirement_ids: list[str] | None = None
    linked_change_ids: list[str] | None = None
    specifications: dict | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)

class InterfaceVerificationCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    verification_type: str = Field(default="review", pattern="^(review|inspection|analysis|test|fit_check|simulation|other)$")
    title: str = Field(min_length=2, max_length=512)
    status: str = Field(default="planned", pattern="^(planned|in_progress|passed|failed|waived)$")
    result_summary: str | None = Field(default=None, max_length=5000)
    measured_result: dict = {}
    evidence_document_ids: list[str] = []
    linked_requirement_verification_id: str | None = None
    performed_at: str | None = None
    notes: str | None = Field(default=None, max_length=5000)

class InterfaceVerificationUpdateRequest(BaseModel):
    verification_type: str | None = Field(default=None, pattern="^(review|inspection|analysis|test|fit_check|simulation|other)$")
    title: str | None = Field(default=None, min_length=2, max_length=512)
    status: str | None = Field(default=None, pattern="^(planned|in_progress|passed|failed|waived)$")
    result_summary: str | None = Field(default=None, max_length=5000)
    measured_result: dict | None = None
    evidence_document_ids: list[str] | None = None
    linked_requirement_verification_id: str | None = None
    performed_at: str | None = None
    notes: str | None = Field(default=None, max_length=5000)


class VehicleVariantCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    name: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    status: str = Field(default="active", pattern="^(draft|active|released|obsolete)$")
    vehicle_class: str | None = Field(default=None, pattern="^(passenger_car|lcv|truck|bus|special_vehicle|component)$")
    powertrain_type: str | None = Field(default=None, pattern="^(ice|hev|phev|bev|fcev|other)$")
    drivetrain: str | None = Field(default=None, max_length=64)
    wheelbase_mm: int | None = Field(default=None, ge=1000, le=15000)
    axle_configuration: str | None = Field(default=None, max_length=64)
    plant: str | None = Field(default=None, max_length=96)
    cab_type: str | None = Field(default=None, max_length=96)
    gross_vehicle_weight_t: float | None = Field(default=None, ge=0, le=200)
    payload_t: float | None = Field(default=None, ge=0, le=200)
    battery_kwh: float | None = Field(default=None, ge=0, le=5000)
    model_year: str | None = Field(default=None, max_length=32)
    market: str | None = Field(default=None, max_length=96)
    body_style: str | None = Field(default=None, max_length=96)
    engine: str | None = Field(default=None, max_length=128)
    transmission: str | None = Field(default=None, max_length=128)
    trim: str | None = Field(default=None, max_length=128)
    supplier_strategy: str | None = Field(default=None, max_length=255)
    attributes: dict = {}
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)

class VehicleVariantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, pattern="^(draft|active|released|obsolete)$")
    vehicle_class: str | None = Field(default=None, pattern="^(passenger_car|lcv|truck|bus|special_vehicle|component)$")
    powertrain_type: str | None = Field(default=None, pattern="^(ice|hev|phev|bev|fcev|other)$")
    drivetrain: str | None = Field(default=None, max_length=64)
    wheelbase_mm: int | None = Field(default=None, ge=1000, le=15000)
    axle_configuration: str | None = Field(default=None, max_length=64)
    plant: str | None = Field(default=None, max_length=96)
    cab_type: str | None = Field(default=None, max_length=96)
    gross_vehicle_weight_t: float | None = Field(default=None, ge=0, le=200)
    payload_t: float | None = Field(default=None, ge=0, le=200)
    battery_kwh: float | None = Field(default=None, ge=0, le=5000)
    model_year: str | None = Field(default=None, max_length=32)
    market: str | None = Field(default=None, max_length=96)
    body_style: str | None = Field(default=None, max_length=96)
    engine: str | None = Field(default=None, max_length=128)
    transmission: str | None = Field(default=None, max_length=128)
    trim: str | None = Field(default=None, max_length=128)
    supplier_strategy: str | None = Field(default=None, max_length=255)
    attributes: dict | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)

class ConfigurationApplicabilityCreateRequest(BaseModel):
    variant_id: str
    entity_type: str = Field(pattern="^(part|document|architecture_node|interface|requirement|change)$")
    entity_key: str = Field(min_length=1, max_length=255)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    applicability: str = Field(default="included", pattern="^(included|excluded)$")
    source: str = Field(default="manual", pattern="^(manual|bom|plm|rule|import)$")
    effectivity_from: str | None = Field(default=None, max_length=64)
    effectivity_to: str | None = Field(default=None, max_length=64)
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)

class ConfigurationApplicabilityUpdateRequest(BaseModel):
    applicability: str | None = Field(default=None, pattern="^(included|excluded)$")
    source: str | None = Field(default=None, pattern="^(manual|bom|plm|rule|import)$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    effectivity_from: str | None = Field(default=None, max_length=64)
    effectivity_to: str | None = Field(default=None, max_length=64)
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)

class ReleaseBaselineCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    name: str = Field(min_length=2, max_length=512)
    baseline_type: str = Field(default="release", pattern="^(design_freeze|release|sop|audit|other)$")
    variant_id: str | None = None
    manufacturing_area: str | None = Field(default=None, max_length=64)
    root_part_number: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=5000)


class ChangeSimulationRequest(BaseModel):
    part_number: str = Field(min_length=1, max_length=128)
    from_revision: str | None = Field(default=None, max_length=64)
    to_revision: str | None = Field(default=None, max_length=64)
    material_from: str | None = Field(default=None, max_length=255)
    material_to: str | None = Field(default=None, max_length=255)
    thickness_from_mm: float | None = None
    thickness_to_mm: float | None = None
    supplier_from: str | None = Field(default=None, max_length=512)
    supplier_to: str | None = Field(default=None, max_length=512)
    unit_cost_from: float | None = None
    unit_cost_to: float | None = None
    quantity_from: float | None = None
    quantity_to: float | None = None
    quantity_per_vehicle: float | None = Field(default=1.0, gt=0)
    annual_volume: int | None = Field(default=None, ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    geometry_changed: bool = False
    notes: str | None = Field(default=None, max_length=3000)


class DigitalThreadAskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    focus_part: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=8, ge=1, le=20)
    conversation: list[dict] = []


class KnowledgeMemoryAskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    part_number: str | None = Field(default=None, max_length=128)
    scope: str = Field(default="project", pattern="^(project|portfolio)$")
    source_types: list[str] = []
    limit: int = Field(default=10, ge=1, le=30)


class KnowledgeLessonPromoteRequest(BaseModel):
    case_id: str = Field(min_length=3, max_length=128)
    title: str | None = Field(default=None, max_length=512)
    problem: str | None = Field(default=None, max_length=5000)
    decision: str | None = Field(default=None, max_length=5000)
    outcome: str | None = Field(default=None, max_length=5000)
    effectiveness: str = Field(default="unknown", pattern="^(unknown|positive|mixed|negative|verified)$")
    tags: list[str] = []


class KnowledgeLessonUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(draft|validated|archived)$")
    outcome: str | None = Field(default=None, max_length=5000)
    effectiveness: str | None = Field(default=None, pattern="^(unknown|positive|mixed|negative|verified)$")

# --- v5.3 Closed-Loop Engineering Intelligence ---
class EngineeringDecisionCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    title: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    change_id: str | None = None
    problem_statement: str = Field(min_length=3, max_length=10000)
    alternatives: list[dict] = []
    chosen_option: str = Field(min_length=1, max_length=5000)
    rationale: str = Field(min_length=2, max_length=10000)
    expected_result: str | None = Field(default=None, max_length=5000)
    accepted_risk: str = Field(default="unknown", pattern="^(unknown|low|medium|high|critical)$")
    owner: str | None = Field(default=None, max_length=255)
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class EngineeringDecisionUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(draft|approved|implemented|verified|closed|cancelled)$")
    expected_result: str | None = Field(default=None, max_length=5000)
    effectiveness_status: str | None = Field(default=None, pattern="^(not_reviewed|observing|effective|ineffective|inconclusive)$")
    effectiveness_summary: str | None = Field(default=None, max_length=5000)
    evidence_document_ids: list[str] | None = None


class ProductionFeedbackCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    change_id: str | None = None
    decision_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    supplier_code: str | None = Field(default=None, max_length=128)
    observation_from: str | None = None
    observation_to: str | None = None
    built_quantity: int = Field(default=0, ge=0)
    defect_quantity: int = Field(default=0, ge=0)
    before_defect_rate_pct: float | None = Field(default=None, ge=0)
    planned_cost_delta: float | None = None
    actual_cost_delta: float | None = None
    planned_mass_delta_kg: float | None = None
    actual_mass_delta_kg: float | None = None
    planned_cycle_time_delta_sec: float | None = None
    actual_cycle_time_delta_sec: float | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: str = Field(default="observing", pattern="^(observing|complete|superseded)$")
    metrics: dict = {}
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class ChangeEffectivenessCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    change_id: str
    decision_id: str | None = None
    feedback_id: str | None = None
    target_description: str = Field(min_length=2, max_length=5000)
    baseline_value: float | None = None
    target_value: float | None = None
    observed_value: float | None = None
    unit: str | None = Field(default=None, max_length=64)
    population: int | None = Field(default=None, ge=0)
    status: str = Field(default="observation", pattern="^(observation|effective|ineffective|inconclusive)$")
    conclusion: str | None = Field(default=None, max_length=5000)
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class EngineeringDeviationCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str = Field(min_length=1, max_length=128)
    released_revision: str | None = Field(default=None, max_length=64)
    requested_revision: str | None = Field(default=None, max_length=64)
    reason: str = Field(min_length=3, max_length=5000)
    quantity_limit: int | None = Field(default=None, ge=1)
    valid_from: str | None = None
    valid_until: str | None = None
    affected_variant_ids: list[str] = []
    risks: list[dict] = []
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class EngineeringDeviationUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(draft|approved|active|closed|cancelled)$")
    approvals: list[dict] | None = None
    risks: list[dict] | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


class EngineeringRiskCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    title: str = Field(min_length=2, max_length=512)
    description: str | None = Field(default=None, max_length=5000)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    change_id: str | None = None
    supplier_code: str | None = Field(default=None, max_length=128)
    probability: int = Field(default=1, ge=1, le=5)
    severity: int = Field(default=1, ge=1, le=5)
    detectability: int = Field(default=1, ge=1, le=5)
    owner: str | None = Field(default=None, max_length=255)
    mitigations: list[dict] = []
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class EngineeringRiskUpdateRequest(BaseModel):
    residual_probability: int | None = Field(default=None, ge=1, le=5)
    residual_severity: int | None = Field(default=None, ge=1, le=5)
    residual_detectability: int | None = Field(default=None, ge=1, le=5)
    status: str | None = Field(default=None, pattern="^(open|mitigating|accepted|closed)$")
    mitigations: list[dict] | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


# --- v5.4 Engineering Program Control / Launch Command Center ---
class ProgramDependencyCreateRequest(BaseModel):
    predecessor_milestone_id: str
    successor_milestone_id: str
    manufacturing_area: str | None = Field(default=None, max_length=64)
    dependency_type: str = Field(default="finish_to_start", pattern="^(finish_to_start)$")
    lag_days: int = Field(default=0, ge=0, le=3650)
    criticality: str = Field(default="normal", pattern="^(normal|high|critical)$")
    owner: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}


class ProgramDependencyUpdateRequest(BaseModel):
    lag_days: int | None = Field(default=None, ge=0, le=3650)
    criticality: str | None = Field(default=None, pattern="^(normal|high|critical)$")
    owner: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)


class ProgramSlipSimulationRequest(BaseModel):
    milestone_id: str
    slip_days: int = Field(ge=1, le=3650)

# --- v5.5 Configuration & Release Assurance ---
class ManufacturingBOMItemCreateRequest(BaseModel):
    variant_id: str | None = None
    manufacturing_area: str | None = Field(default=None, max_length=64)
    parent_part_number: str = Field(min_length=1, max_length=128)
    parent_revision: str | None = Field(default=None, max_length=64)
    child_part_number: str = Field(min_length=1, max_length=128)
    child_revision: str | None = Field(default=None, max_length=64)
    quantity: float = Field(default=1.0, gt=0)
    unit: str = Field(default="pcs", min_length=1, max_length=32)
    position: str | None = Field(default=None, max_length=64)
    operation_code: str | None = Field(default=None, max_length=96)
    supplier_code: str | None = Field(default=None, max_length=128)
    source_system: str = Field(default="manual", pattern="^(manual|erp|mes|plm|import|api)$")
    source_document_id: str | None = None
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class ConfigurationEffectivityCreateRequest(BaseModel):
    variant_id: str | None = None
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    plant: str | None = Field(default=None, max_length=255)
    market: str | None = Field(default=None, max_length=96)
    supplier_code: str | None = Field(default=None, max_length=128)
    vin_from: str | None = Field(default=None, max_length=128)
    vin_to: str | None = Field(default=None, max_length=128)
    serial_from: int | None = Field(default=None, ge=0)
    serial_to: int | None = Field(default=None, ge=0)
    effective_from: str | None = None
    effective_to: str | None = None
    status: str = Field(default="active", pattern="^(draft|active|obsolete|cancelled)$")
    source: str = Field(default="manual", pattern="^(manual|plm|erp|mes|rule|import|api)$")
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}


class ChangeCutInCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    change_id: str | None = None
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str = Field(min_length=1, max_length=128)
    from_revision: str | None = Field(default=None, max_length=64)
    to_revision: str = Field(min_length=1, max_length=64)
    variant_ids: list[str] = []
    plant: str | None = Field(default=None, max_length=255)
    line_id: str | None = None
    cut_in_at: str | None = None
    vin_from: str | None = Field(default=None, max_length=128)
    old_stock_qty: int | None = Field(default=None, ge=0)
    new_stock_qty: int | None = Field(default=None, ge=0)
    old_stock_disposition: str | None = Field(default=None, pattern="^(use_as_is|rework|return_supplier|scrap|conditional_use)$")
    logistics_confirmed: bool = False
    status: str = Field(default="planned", pattern="^(draft|planned|ready|active|complete|cancelled)$")
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}


class AsBuiltConfigurationCreateRequest(BaseModel):
    vehicle_identifier: str = Field(min_length=1, max_length=128)
    variant_id: str | None = None
    manufacturing_area: str | None = Field(default=None, max_length=64)
    plant: str | None = Field(default=None, max_length=255)
    built_at: str | None = None
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    deviation_id: str | None = None
    source_system: str = Field(default="import", pattern="^(manual|mes|erp|import|api)$")
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class PartSupersessionCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    old_part_number: str = Field(min_length=1, max_length=128)
    old_revision: str | None = Field(default=None, max_length=64)
    new_part_number: str = Field(min_length=1, max_length=128)
    new_revision: str | None = Field(default=None, max_length=64)
    interchangeable: bool = False
    retrofit_allowed: bool = False
    stock_use_allowed: bool = False
    status: str = Field(default="active", pattern="^(draft|active|obsolete|cancelled)$")
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}

class ConfigurationAssuranceAskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    variant_id: str | None = None
    vehicle_identifier: str | None = Field(default=None, max_length=128)
    manufacturing_area: str | None = Field(default=None, max_length=64)

# --- v5.6 Vehicle Build & Launch Intelligence ---
class VehicleBuildCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    vehicle_identifier: str = Field(min_length=1, max_length=128)
    variant_id: str | None = None
    manufacturing_area: str | None = Field(default=None, max_length=64)
    plant: str | None = Field(default=None, max_length=255)
    line_id: str | None = None
    build_type: str = Field(default="pilot", pattern="^(pilot|pre_series|safe_launch|series_observation)$")
    build_sequence: int | None = Field(default=None, ge=0)
    planned_at: str | None = None
    completed_at: str | None = None
    status: str = Field(default="planned", pattern="^(planned|in_progress|completed|passed|failed|cancelled)$")
    release_baseline_id: str | None = None
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}


class BuildGenealogyCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    lot_number: str | None = Field(default=None, max_length=128)
    serial_number: str | None = Field(default=None, max_length=128)
    quantity: float = Field(default=1.0, gt=0)
    installed_at: str | None = None
    source_system: str = Field(default="import", pattern="^(manual|mes|erp|scan|import|api)$")
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class BuildDefectLinkCreateRequest(BaseModel):
    defect_id: str
    detection_stage: str = Field(default="build", pattern="^(incoming|build|eol|audit|road_test|field_simulation)$")
    containment_status: str = Field(default="open", pattern="^(open|contained|released|closed)$")
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)


class SafeLaunchControlCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    supplier_code: str | None = Field(default=None, max_length=128)
    characteristic: str = Field(min_length=1, max_length=512)
    status: str = Field(default="active", pattern="^(draft|active|exit_candidate|exited|cancelled)$")
    inspected_quantity: int = Field(default=0, ge=0)
    defect_quantity: int = Field(default=0, ge=0)
    consecutive_clean_builds: int = Field(default=0, ge=0)
    required_clean_builds: int = Field(default=3, ge=1, le=1000)
    required_inspected_quantity: int = Field(default=100, ge=1)
    exit_criteria: dict = {}
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}


class SafeLaunchControlUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(draft|active|exit_candidate|exited|cancelled)$")
    inspected_quantity: int | None = Field(default=None, ge=0)
    defect_quantity: int | None = Field(default=None, ge=0)
    consecutive_clean_builds: int | None = Field(default=None, ge=0)
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)

# --- v5.7 Series Quality & Manufacturing Intelligence ---
class SeriesQualityObservationCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    plant: str | None = Field(default=None, max_length=255)
    line_id: str | None = None
    station_id: str | None = None
    operation_id: str | None = None
    shift_code: str | None = Field(default=None, max_length=64)
    variant_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_lot: str | None = Field(default=None, max_length=128)
    defect_code: str | None = Field(default=None, max_length=64)
    characteristic: str | None = Field(default=None, max_length=512)
    produced_quantity: int = Field(default=0, ge=0)
    inspected_quantity: int = Field(default=0, ge=0)
    defect_quantity: int = Field(default=0, ge=0)
    detected_in_process_quantity: int = Field(default=0, ge=0)
    escaped_quantity: int = Field(default=0, ge=0)
    scrap_cost: float = Field(default=0, ge=0)
    rework_cost: float = Field(default=0, ge=0)
    containment_cost: float = Field(default=0, ge=0)
    warranty_cost_estimate: float = Field(default=0, ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    observed_at: str | None = None
    period_key: str | None = Field(default=None, max_length=64)
    source_system: str = Field(default="import", pattern="^(manual|mes|qms|erp|import|api)$")
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class ProcessCapabilityCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    plant: str | None = Field(default=None, max_length=255)
    line_id: str | None = None
    station_id: str | None = None
    operation_id: str | None = None
    asset_id: str | None = None
    part_number: str | None = Field(default=None, max_length=128)
    supplier_code: str | None = Field(default=None, max_length=128)
    characteristic: str = Field(min_length=1, max_length=512)
    unit: str | None = Field(default=None, max_length=64)
    sample_size: int = Field(default=0, ge=0)
    mean_value: float | None = None
    sigma_value: float | None = Field(default=None, ge=0)
    lower_spec_limit: float | None = None
    upper_spec_limit: float | None = None
    cp: float | None = Field(default=None, ge=0)
    cpk: float | None = None
    pp: float | None = Field(default=None, ge=0)
    ppk: float | None = None
    measured_at: str | None = None
    source_system: str = Field(default="import", pattern="^(manual|mes|qms|spc|import|api)$")
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class SuspectPopulationRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_lot: str | None = Field(default=None, max_length=128)
    plant: str | None = Field(default=None, max_length=255)
    variant_id: str | None = None
    built_from: str | None = None
    built_to: str | None = None
    max_results: int = Field(default=5000, ge=1, le=10000)


class SeriesContainmentCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    part_number: str | None = Field(default=None, max_length=128)
    defect_code: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    supplier_lot: str | None = Field(default=None, max_length=128)
    status: str = Field(default="open", pattern="^(open|contained|effective|closed|cancelled)$")
    suspect_criteria: dict = {}
    suspect_vehicle_identifiers: list[str] = []
    inspected_quantity: int = Field(default=0, ge=0)
    defect_quantity: int = Field(default=0, ge=0)
    actions: list = []
    linked_8d_id: str | None = None
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}


class SeriesContainmentUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|contained|effective|closed|cancelled)$")
    inspected_quantity: int | None = Field(default=None, ge=0)
    defect_quantity: int | None = Field(default=None, ge=0)
    actions: list | None = None
    suspect_vehicle_identifiers: list[str] | None = None
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)


class FieldQualityClaimCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    claim_reference: str = Field(min_length=1, max_length=128)
    vehicle_identifier: str | None = Field(default=None, max_length=128)
    part_number: str | None = Field(default=None, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    failure_mode: str = Field(min_length=1, max_length=512)
    failure_family: str | None = Field(default=None, max_length=255)
    mileage_km: float | None = Field(default=None, ge=0)
    in_service_at: str | None = None
    market: str | None = Field(default=None, max_length=96)
    climate_zone: str | None = Field(default=None, max_length=96)
    dealer_code: str | None = Field(default=None, max_length=128)
    repair_code: str | None = Field(default=None, max_length=128)
    repair_method: str | None = Field(default=None, max_length=512)
    no_trouble_found: bool = False
    repeat_repair: bool = False
    part_cost: float = Field(default=0, ge=0)
    labor_cost: float = Field(default=0, ge=0)
    logistics_cost: float = Field(default=0, ge=0)
    dealer_handling_cost: float = Field(default=0, ge=0)
    source_system: str = Field(default="import", pattern="^(manual|warranty|dms|fleet|service|import|api)$")
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    status: str = Field(default="open", pattern="^(open|investigating|contained|closed|cancelled)$")
    claim_at: str | None = None
    cost_estimate: float = Field(default=0, ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    linked_8d_id: str | None = None
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class SeriesIntelligenceAskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    manufacturing_area: str | None = Field(default=None, max_length=64)


# --- v5.8 Field Reliability & Product Lifecycle Intelligence ---
class FieldReliabilityExposureCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str = Field(min_length=1, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    market: str | None = Field(default=None, max_length=96)
    climate_zone: str | None = Field(default=None, max_length=96)
    population_count: int = Field(ge=0)
    censored_count: int = Field(default=0, ge=0)
    censor_mileage_km: float | None = Field(default=None, ge=0)
    total_exposure_km: float | None = Field(default=None, ge=0)
    as_of_at: str | None = None
    source_system: str = Field(default="import", pattern="^(manual|warranty|dms|fleet|erp|import|api)$")
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class DesignFMEAItemCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    part_number: str | None = Field(default=None, max_length=128)
    function: str | None = Field(default=None, max_length=512)
    failure_mode: str = Field(min_length=1, max_length=512)
    effect: str | None = Field(default=None, max_length=5000)
    cause: str | None = Field(default=None, max_length=5000)
    prevention_control: str | None = Field(default=None, max_length=5000)
    detection_control: str | None = Field(default=None, max_length=5000)
    severity: int = Field(default=1, ge=1, le=10)
    occurrence: int = Field(default=1, ge=1, le=10)
    detection: int = Field(default=1, ge=1, le=10)
    action_priority: str | None = Field(default=None, max_length=16)
    status: str = Field(default="open", pattern="^(open|review|controlled|closed)$")
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class FieldServiceActionCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._/-]+$")
    manufacturing_area: str | None = Field(default=None, max_length=64)
    action_type: str = Field(default="tsb", pattern="^(tsb|field_containment|campaign_assessment)$")
    title: str = Field(min_length=1, max_length=512)
    status: str = Field(default="draft", pattern="^(draft|review|active|completed|closed|cancelled)$")
    part_number: str | None = Field(default=None, max_length=128)
    revision: str | None = Field(default=None, max_length=64)
    supplier_code: str | None = Field(default=None, max_length=128)
    failure_mode: str | None = Field(default=None, max_length=512)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    safety_relevance: str = Field(default="unknown", pattern="^(unknown|no|review_required|confirmed)$")
    applicability: dict = {}
    diagnosis: str | None = Field(default=None, max_length=10000)
    repair: str | None = Field(default=None, max_length=10000)
    suspect_vehicle_identifiers: list[str] = []
    inspected_quantity: int = Field(default=0, ge=0)
    repaired_quantity: int = Field(default=0, ge=0)
    no_defect_quantity: int = Field(default=0, ge=0)
    linked_8d_id: str | None = None
    linked_change_id: str | None = None
    evidence_document_ids: list[str] = []
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = {}


class FieldServiceActionUpdateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(draft|review|active|completed|closed|cancelled)$")
    safety_relevance: str | None = Field(default=None, pattern="^(unknown|no|review_required|confirmed)$")
    applicability: dict | None = None
    diagnosis: str | None = Field(default=None, max_length=10000)
    repair: str | None = Field(default=None, max_length=10000)
    suspect_vehicle_identifiers: list[str] | None = None
    inspected_quantity: int | None = Field(default=None, ge=0)
    repaired_quantity: int | None = Field(default=None, ge=0)
    no_defect_quantity: int | None = Field(default=None, ge=0)
    evidence_document_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    approve: bool | None = None


class FieldReliabilityAskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    vehicle_identifier: str | None = Field(default=None, max_length=128)


class EngineeringWorkflowCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=96)
    workflow_type: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=512)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    priority: str = Field(default="normal", max_length=32)
    owner: str | None = Field(default=None, max_length=255)
    trigger_type: str | None = Field(default=None, max_length=64)
    trigger_id: str | None = Field(default=None, max_length=128)
    target_gate: str | None = Field(default=None, max_length=96)
    due_at: str | None = None
    source_object_refs: list[dict] = Field(default_factory=list, max_length=100)
    evidence_document_ids: list[str] = Field(default_factory=list, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)
    metadata: dict = Field(default_factory=dict)


class EngineeringWorkflowUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    priority: str | None = Field(default=None, max_length=32)
    owner: str | None = Field(default=None, max_length=255)
    complete_current_stage: bool = False
    block_reason: str | None = Field(default=None, max_length=2000)
    evidence_document_ids: list[str] | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)


class EngineeringOSAskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    role: str = Field(default="engineering", max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)


# --- v6.3 Manufacturing Work Instructions & Station Intelligence ---
class BOMTranslationRequest(BaseModel):
    target_language: str = Field(default="ru", pattern="^(ru|en|zh)$")
    source_language: str = Field(default="auto", pattern="^(auto|ru|en|zh)$")
    refresh: bool = False


class WorkInstructionStep(BaseModel):
    sequence: int = Field(default=10, ge=0, le=100000)
    title: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1, max_length=8000)
    media_document_ids: list[str] = []
    safety_note: str | None = Field(default=None, max_length=3000)
    quality_note: str | None = Field(default=None, max_length=3000)
    expected_time_sec: float | None = Field(default=None, ge=0, le=86400)


class WorkInstructionCreateRequest(BaseModel):
    manufacturing_area: str = Field(min_length=1, max_length=64)
    line_id: str | None = None
    station_id: str | None = None
    operation_id: str | None = None
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=2, max_length=512)
    revision: str = Field(default="A", min_length=1, max_length=64)
    instruction_type: str = Field(default="assembly", pattern="^(assembly|inspection|rework|maintenance|logistics|quality|safety|other)$")
    source_language: str = Field(default="ru", pattern="^(auto|ru|en|zh)$")
    source_factory: str | None = Field(default=None, max_length=255)
    source_document_id: str | None = None
    original_text: str | None = Field(default=None, max_length=50000)
    steps: list[WorkInstructionStep] = []
    safety_points: list[str] = []
    quality_points: list[str] = []
    tools: list[str] = []
    ppe: list[str] = []
    required_skill: str | None = Field(default=None, max_length=255)
    operator_role: str | None = Field(default=None, max_length=255)
    cycle_time_sec: float | None = Field(default=None, ge=0, le=86400)
    owner: str | None = Field(default=None, max_length=255)
    evidence_document_ids: list[str] = []
    metadata: dict = {}


class WorkInstructionImportRequest(BaseModel):
    document_id: str
    manufacturing_area: str = Field(min_length=1, max_length=64)
    line_id: str | None = None
    station_id: str | None = None
    operation_id: str | None = None
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=2, max_length=512)
    revision: str = Field(default="A", min_length=1, max_length=64)
    instruction_type: str = Field(default="assembly", pattern="^(assembly|inspection|rework|maintenance|logistics|quality|safety|other)$")
    source_language: str = Field(default="auto", pattern="^(auto|ru|en|zh)$")
    source_factory: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=255)


class WorkInstructionUpdateRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=512)
    status: str | None = Field(default=None, pattern="^(draft|in_review|approved|obsolete)$")
    instruction_type: str | None = Field(default=None, pattern="^(assembly|inspection|rework|maintenance|logistics|quality|safety|other)$")
    line_id: str | None = None
    station_id: str | None = None
    operation_id: str | None = None
    original_text: str | None = Field(default=None, max_length=50000)
    steps: list[WorkInstructionStep] | None = None
    safety_points: list[str] | None = None
    quality_points: list[str] | None = None
    tools: list[str] | None = None
    ppe: list[str] | None = None
    required_skill: str | None = Field(default=None, max_length=255)
    operator_role: str | None = Field(default=None, max_length=255)
    cycle_time_sec: float | None = Field(default=None, ge=0, le=86400)
    owner: str | None = Field(default=None, max_length=255)
    metadata: dict | None = None


class EngineeringTranslationRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    target_language: str = Field(default="ru", pattern="^(ru|en|zh)$")
    force: bool = False


class TranslationReviewRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    decision: str = Field(pattern="^(approve|reject)$")
    notes: str | None = Field(default=None, max_length=3000)


class WorkInstructionAskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    manufacturing_area: str = Field(min_length=1, max_length=64)
    station_id: str | None = None
    operation_id: str | None = None
    limit: int = Field(default=6, ge=1, le=20)


class ManufacturingLayoutCreateRequest(BaseModel):
    manufacturing_area: str = Field(min_length=1, max_length=64)
    line_id: str | None = None
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=2, max_length=512)
    revision: str = Field(default="A", min_length=1, max_length=64)
    source_document_id: str | None = None
    owner: str | None = Field(default=None, max_length=255)
    metadata: dict = {}


class StationLayoutPlacementRequest(BaseModel):
    expected_layout_version: int | None = Field(default=None, ge=1)
    station_id: str
    x_pct: float = Field(ge=0, le=100)
    y_pct: float = Field(ge=0, le=100)
    width_pct: float = Field(default=14, ge=4, le=60)
    height_pct: float = Field(default=12, ge=4, le=60)
    rotation_deg: float = Field(default=0, ge=-360, le=360)
    label_override: str | None = Field(default=None, max_length=255)
    metadata: dict = {}


# --- v6.3.4 Revision / Conflict Management ---
class WorkInstructionRevisionCreateRequest(BaseModel):
    expected_version: int = Field(ge=1)
    new_revision: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=2, max_length=1000)


class ManufacturingLayoutRevisionCreateRequest(BaseModel):
    expected_version: int = Field(ge=1)
    new_revision: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=2, max_length=1000)

# --- v6.3.5 Approval & Release Governance ---
class ApprovalPolicyStage(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    label: str = Field(min_length=1, max_length=255)
    required_role: str = Field(default="engineering_user", pattern="^(engineering_user|engineering_admin|group)$")
    required_groups: list[str] = []
    delegation_allowed: bool = False

class ApprovalPolicyCreateRequest(BaseModel):
    project_code: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    entity_type: str = Field(pattern="^(work_instruction|manufacturing_layout|engineering_change|release_package)$")
    name: str = Field(min_length=2, max_length=255)
    stages: list[ApprovalPolicyStage] = Field(min_length=1, max_length=8)
    maker_checker_required: bool = True
    distinct_approvers_required: bool = True

class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str | None = Field(default=None, max_length=3000)

class ReleasePackageItemRequest(BaseModel):
    entity_type: str = Field(pattern="^(work_instruction|manufacturing_layout|engineering_change|document)$")
    entity_id: str

class ReleasePackageCreateRequest(BaseModel):
    manufacturing_area: str | None = Field(default=None, max_length=64)
    code: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=2, max_length=512)
    source_change_id: str | None = None
    items: list[ReleasePackageItemRequest] = Field(min_length=1, max_length=500)
    metadata: dict = {}


# --- v6.3.6 Enterprise Identity & Policy Enforcement ---
class IdentityPolicyCreateRequest(BaseModel):
    project_code: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    entity_type: str | None = Field(default=None, max_length=64)
    action: str = Field(min_length=2, max_length=96, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    allowed_groups: list[str] = []
    denied_groups: list[str] = []
    required_acr_values: list[str] = []
    require_oidc: bool = False
    max_auth_age_seconds: int | None = Field(default=None, ge=60, le=86400)
    allow_service_accounts: bool = False
    delegation_allowed: bool = False


class IdentityDelegationCreateRequest(BaseModel):
    delegator: str = Field(min_length=1, max_length=255)
    delegate: str = Field(min_length=1, max_length=255)
    project_code: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    entity_type: str | None = Field(default=None, max_length=64)
    actions: list[str] = Field(min_length=1, max_length=16)
    delegated_groups: list[str] = Field(min_length=1, max_length=32)
    valid_from: datetime | None = None
    valid_until: datetime
    reason: str = Field(min_length=3, max_length=3000)


# --- v6.3.7 Engineering Release Handover & Integration Safety ---
class HandoverTargetCreateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=96, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+[A-Za-z0-9]$")
    name: str = Field(min_length=2, max_length=255)
    external_system_id: str = Field(min_length=1, max_length=36)
    environment: str = Field(default="test", pattern="^(dev|test|pilot|prod|production)$")
    allow_write: bool = False
    idempotency_supported: bool = True
    receipt_required: bool = True
    write_path: str = Field(min_length=2, max_length=512)
    reconcile_path_template: str | None = Field(default=None, max_length=512)
    allowed_project_codes: list[str] = []
    allowed_manufacturing_areas: list[str] = []
    metadata: dict = {}

class HandoverJobCreateRequest(BaseModel):
    target_code: str = Field(min_length=3, max_length=96)
    idempotency_key: str = Field(min_length=8, max_length=128)
    mode: str = Field(default="dry_run", pattern="^(dry_run|write)$")

class HandoverAuthorizationRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=3000)

# --- v6.3.8 Data Lifecycle, Retention & Compliance Hardening ---
class RetentionPolicyCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    entity_type: str = Field(min_length=3, max_length=64)
    project_code: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    archive_after_days: int | None = Field(default=None, ge=0, le=36500)
    retain_for_days: int = Field(default=3650, ge=1, le=36500)
    immutable_min_days: int = Field(default=0, ge=0, le=36500)
    allow_authoritative_purge: bool = False

class LegalHoldCreateRequest(BaseModel):
    hold_code: str = Field(min_length=3, max_length=96, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    project_code: str | None = Field(default=None, max_length=64)
    manufacturing_area: str | None = Field(default=None, max_length=64)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=36)
    reason: str = Field(min_length=5, max_length=4000)
    expires_at: datetime | None = None

class LegalHoldReleaseRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=3000)

class LifecycleArchiveRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=3000)

class PurgeRequestCreateRequest(BaseModel):
    entity_type: str = Field(min_length=3, max_length=64)
    entity_id: str = Field(min_length=1, max_length=36)
    purge_scope: str = Field(default="projections_only", pattern="^(projections_only|authoritative)$")
    reason: str = Field(min_length=5, max_length=4000)
