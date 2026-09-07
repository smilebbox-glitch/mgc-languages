import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class IssueSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class IssueStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    phase: Mapped[str] = mapped_column(String(64), default="development", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    root_part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    target_release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acl_groups: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProjectArea(Base):
    __tablename__ = "project_areas"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_project_area_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acl_groups: Mapped[list[str]] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_project_milestone_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gate: Mapped[str] = mapped_column(String(64), default="engineering")
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(255), default="application/octet-stream")
    extension: Mapped[str] = mapped_column(String(32), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.uploaded)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    revision: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    acl_groups: Mapped[list[str]] = mapped_column(JSON, default=list)
    extracted_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    preview_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    indexed_chunks: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Part(Base):
    __tablename__ = "parts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_number: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    latest_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PartRevision(Base):
    __tablename__ = "part_revisions"
    __table_args__ = (UniqueConstraint("part_number", "revision", name="uq_part_revision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BOMItem(Base):
    __tablename__ = "bom_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_bom_quantity_positive"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_part_number: Mapped[str] = mapped_column(String(128), index=True)
    parent_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    child_part_number: Mapped[str] = mapped_column(String(128), index=True)
    child_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(32), default="pcs")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    source_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)




class EngineeringTranslationMemory(Base):
    __tablename__ = "engineering_translation_memory"
    __table_args__ = (UniqueConstraint("project_code", "scope", "source_hash", "target_language", name="uq_translation_memory_scope_hash_target"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(64), default="engineering", index=True)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_language: Mapped[str] = mapped_column(String(16), default="auto", index=True)
    target_language: Mapped[str] = mapped_column(String(16), default="ru", index=True)
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Relationship(Base):
    __tablename__ = "relationships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_type: Mapped[str] = mapped_column(String(64), index=True)
    subject_id: Mapped[str] = mapped_column(String(256), index=True)
    predicate: Mapped[str] = mapped_column(String(128), index=True)
    object_type: Mapped[str] = mapped_column(String(64), index=True)
    object_id: Mapped[str] = mapped_column(String(256), index=True)
    evidence_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ValidationIssue(Base):
    __tablename__ = "validation_issues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    revision: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    severity: Mapped[IssueSeverity] = mapped_column(Enum(IssueSeverity), default=IssueSeverity.warning)
    status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus), default=IssueStatus.open)
    rule_code: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class DocumentActivity(Base):
    """Append-only, tamper-evident activity trail for one engineering document.

    The database is still the system of record; previous_hash/event_hash make silent
    row edits or deletions detectable during review/export.
    """
    __tablename__ = "document_activities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    user: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    summary: Mapped[str] = mapped_column(String(1024))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class DocumentActivityState(Base):
    """Per-document chain anchor used to detect tail deletion and serialize audit head state."""
    __tablename__ = "document_activity_states"
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), primary_key=True)
    head_hash: Mapped[str] = mapped_column(String(64), default="")
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class ComputeJob(Base):
    __tablename__ = "compute_jobs"
    __table_args__ = (
        CheckConstraint("priority >= 0 AND priority <= 9", name="ck_compute_job_priority_range"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="ck_compute_job_progress_range"),
        CheckConstraint("attempt_count >= 0 AND max_attempts >= 1", name="ck_compute_job_attempts"),
        CheckConstraint("dispatch_generation >= 0 AND recovery_count >= 0", name="ck_compute_job_recovery_counters"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    celery_task_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    dispatch_token: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    dispatch_generation: Mapped[int] = mapped_column(Integer, default=0)
    last_dispatch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    user: Mapped[str] = mapped_column(String(255), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    resource_class: Mapped[str] = mapped_column(String(32), default="cpu", index=True)
    queue: Mapped[str] = mapped_column(String(64), default="cpu", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=4, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=1800)
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recovery_count: Mapped[int] = mapped_column(Integer, default=0)
    last_recovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recovery_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ComputeJobRecoveryEvent(Base):
    __tablename__ = "compute_job_recovery_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("compute_jobs.id"), index=True)
    recovery_number: Mapped[int] = mapped_column(Integer, default=1, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(String(512))
    actor: Mapped[str] = mapped_column(String(255), default="scheduler", index=True)
    prior_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prior_worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prior_celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prior_dispatch_generation: Mapped[int] = mapped_column(Integer, default=0)
    new_dispatch_generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ReviewStatus(str, enum.Enum):
    draft = "draft"
    running = "running"
    review_required = "review_required"
    approved = "approved"
    rejected = "rejected"


class ChangeRequest(Base):
    __tablename__ = "change_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": row_version}
    code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    eco_code: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    from_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="normal", index=True)
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    owner: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), index=True, default="system")
    impact_json: Mapped[dict] = mapped_column(JSON, default=dict)
    affected_parts: Mapped[list] = mapped_column(JSON, default=list)
    affected_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    design_review_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("design_reviews.id"), nullable=True)
    implementation_plan: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_plan: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChangeApproval(Base):
    __tablename__ = "change_approvals"
    __table_args__ = (UniqueConstraint("change_id", "stage", name="uq_change_approval_stage_once"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    change_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_requests.id"), index=True)
    stage: Mapped[str] = mapped_column(String(64), index=True)
    approver: Mapped[str] = mapped_column(String(255), index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ChangeEvent(Base):
    __tablename__ = "change_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    change_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_requests.id"), index=True)
    user: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    summary: Mapped[str] = mapped_column(String(1024))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ChangeEventState(Base):
    __tablename__ = "change_event_states"
    change_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_requests.id"), primary_key=True)
    head_hash: Mapped[str] = mapped_column(String(64), default="")
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DesignReview(Base):
    __tablename__ = "design_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str] = mapped_column(String(64), index=True)
    baseline_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.draft)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ReviewApproval(Base):
    __tablename__ = "review_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id: Mapped[str] = mapped_column(String(36), ForeignKey("design_reviews.id"), index=True)
    approver: Mapped[str] = mapped_column(String(255), index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SupplierEvidence(Base):
    __tablename__ = "supplier_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_code: Mapped[str] = mapped_column(String(128), index=True)
    supplier_name: Mapped[str] = mapped_column(String(512))
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    localization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidencePack(Base):
    __tablename__ = "evidence_packs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pack_type: Mapped[str] = mapped_column(String(64), index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExternalSystem(Base):
    __tablename__ = "external_systems"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    connector_type: Mapped[str] = mapped_column(String(64), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    secret_config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    acl_groups: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_health_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_domain: Mapped[str] = mapped_column(String(32), default="engineering", index=True)
    contract_version: Mapped[str] = mapped_column(String(64), default="mgc-integration-v1")
    expected_freshness_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_quality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    last_quality_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SyncCursor(Base):
    __tablename__ = "sync_cursors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_systems.id"), unique=True, index=True)
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ExternalObject(Base):
    __tablename__ = "external_objects"
    __table_args__ = (UniqueConstraint("system_id", "external_id", name="uq_external_object"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_systems.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(512), index=True)
    object_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), index=True, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    data_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_confidence_level: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    data_quality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IntegrationRun(Base):
    __tablename__ = "integration_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_systems.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="running")
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    quarantined_count: Mapped[int] = mapped_column(Integer, default=0)
    replayed_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationIngestEvent(Base):
    __tablename__ = "integration_ingest_events"
    __table_args__ = (UniqueConstraint("system_id", "idempotency_key", name="uq_integration_ingest_event_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_systems.id"), index=True)
    integration_run_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("integration_runs.id"), nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(512), index=True)
    object_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    contract_version: Mapped[str] = mapped_column(String(64), default="mgc-integration-v1")
    source_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    payload_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    quarantine_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    validation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict)
    first_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationEntityMapping(Base):
    """Human-confirmed external identifier mapping used by reconciliation.

    Exact canonical keys do not require a persisted row. This registry is only for aliases
    or explicit cross-system identities and never changes the authoritative source record.
    """
    __tablename__ = "integration_entity_mappings"
    __table_args__ = (
        UniqueConstraint("system_id", "source_entity_type", "source_external_id", "source_key", "canonical_entity_type", name="uq_integration_entity_mapping"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_systems.id"), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_entity_type: Mapped[str] = mapped_column(String(64), index=True)
    source_external_id: Mapped[str] = mapped_column(String(512), index=True)
    source_key: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    canonical_entity_type: Mapped[str] = mapped_column(String(64), index=True)
    canonical_key: Mapped[str] = mapped_column(String(512), index=True)
    mapping_method: Mapped[str] = mapped_column(String(32), default="manual", index=True)
    status: Mapped[str] = mapped_column(String(32), default="confirmed", index=True)
    source_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CadConversionJob(Base):
    __tablename__ = "cad_conversion_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    source_format: Mapped[str] = mapped_column(String(32))
    target_format: Mapped[str] = mapped_column(String(32), default="step")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    gateway_system_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("external_systems.id"), nullable=True)
    output_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ExternalObjectVersion(Base):
    __tablename__ = "external_object_versions"
    __table_args__ = (UniqueConstraint("system_id", "external_id", "source_fingerprint", name="uq_external_object_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_systems.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(512), index=True)
    source_fingerprint: Mapped[str] = mapped_column(String(256), index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class APQPDeliverable(Base):
    __tablename__ = "apqp_deliverables"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_apqp_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    phase: Mapped[str] = mapped_column(String(64), default="planning", index=True)
    title: Mapped[str] = mapped_column(String(512))
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    linked_part_numbers: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SpecialCharacteristic(Base):
    __tablename__ = "special_characteristics"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_special_characteristic_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(64), default="critical", index=True)
    symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(String(1024))
    specification: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    source_reference_json: Mapped[dict] = mapped_column(JSON, default=dict)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PFMEAItem(Base):
    __tablename__ = "pfmea_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    process_step: Mapped[str] = mapped_column(String(512))
    process_operation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_operations.id"), nullable=True, index=True)
    function: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_mode: Mapped[str] = mapped_column(Text)
    effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    prevention_control: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection_control: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[int] = mapped_column(Integer, default=1)
    occurrence: Mapped[int] = mapped_column(Integer, default=1)
    detection: Mapped[int] = mapped_column(Integer, default=1)
    action_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    special_characteristic_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ControlPlanItem(Base):
    __tablename__ = "control_plan_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    process_step: Mapped[str] = mapped_column(String(512))
    process_operation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_operations.id"), nullable=True, index=True)
    characteristic_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("special_characteristics.id"), nullable=True, index=True)
    characteristic: Mapped[str] = mapped_column(String(1024))
    specification: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    measurement_method: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sample_size: Mapped[str | None] = mapped_column(String(128), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reaction_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_phase: Mapped[str] = mapped_column(String(32), default="production", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PPAPSubmission(Base):
    __tablename__ = "ppap_submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    customer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submission_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    element_status_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Problem8D(Base):
    __tablename__ = "problems_8d"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    complaint_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    team_json: Mapped[list] = mapped_column(JSON, default=list)
    disciplines_json: Mapped[dict] = mapped_column(JSON, default=dict)
    linked_change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ManufacturingLine(Base):
    __tablename__ = "manufacturing_lines"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_manufacturing_line_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProcessStation(Base):
    __tablename__ = "process_stations"
    __table_args__ = (
        UniqueConstraint("line_id", "code", name="uq_process_station_line_code"),
        CheckConstraint("headcount >= 1", name="ck_process_station_headcount_positive"),
        CheckConstraint("takt_time_sec IS NULL OR takt_time_sec >= 0", name="ck_process_station_takt_nonnegative"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": row_version}
    line_id: Mapped[str] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    sequence: Mapped[int] = mapped_column(Integer, default=100)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operator_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    work_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    takt_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProcessOperation(Base):
    __tablename__ = "process_operations"
    __table_args__ = (UniqueConstraint("station_id", "code", name="uq_process_operation_station_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("process_stations.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    sequence: Mapped[int] = mapped_column(Integer, default=100)
    operation_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    cycle_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    work_instruction_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)




class WorkInstruction(Base):
    __tablename__ = "work_instructions"
    __table_args__ = (
        UniqueConstraint("project_code", "code", "revision", name="uq_work_instruction_project_code_revision"),
        CheckConstraint("cycle_time_sec IS NULL OR cycle_time_sec >= 0", name="ck_work_instruction_cycle_nonnegative"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": row_version}
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str] = mapped_column(String(64), index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    station_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_stations.id"), nullable=True, index=True)
    operation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_operations.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    title: Mapped[str] = mapped_column(String(512))
    revision: Mapped[str] = mapped_column(String(64), default="A", index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    instruction_type: Mapped[str] = mapped_column(String(64), default="assembly", index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="authored", index=True)
    source_language: Mapped[str] = mapped_column(String(16), default="ru", index=True)
    source_factory: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_text_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation_status: Mapped[str] = mapped_column(String(32), default="not_required", index=True)
    steps_json: Mapped[list] = mapped_column(JSON, default=list)
    translated_steps_json: Mapped[list] = mapped_column(JSON, default=list)
    safety_points_json: Mapped[list] = mapped_column(JSON, default=list)
    quality_points_json: Mapped[list] = mapped_column(JSON, default=list)
    tools_json: Mapped[list] = mapped_column(JSON, default=list)
    ppe_json: Mapped[list] = mapped_column(JSON, default=list)
    required_skill: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operator_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cycle_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ManufacturingLayout(Base):
    __tablename__ = "manufacturing_layouts"
    __table_args__ = (UniqueConstraint("project_code", "code", "revision", name="uq_manufacturing_layout_project_code_revision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": row_version}
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str] = mapped_column(String(64), index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    title: Mapped[str] = mapped_column(String(512))
    revision: Mapped[str] = mapped_column(String(64), default="A", index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StationLayoutPlacement(Base):
    __tablename__ = "station_layout_placements"
    __table_args__ = (
        UniqueConstraint("layout_id", "station_id", name="uq_station_layout_placement"),
        CheckConstraint("x_pct >= 0 AND x_pct <= 100", name="ck_station_layout_x_pct"),
        CheckConstraint("y_pct >= 0 AND y_pct <= 100", name="ck_station_layout_y_pct"),
        CheckConstraint("width_pct >= 4 AND width_pct <= 60", name="ck_station_layout_width_pct"),
        CheckConstraint("height_pct >= 4 AND height_pct <= 60", name="ck_station_layout_height_pct"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    layout_id: Mapped[str] = mapped_column(String(36), ForeignKey("manufacturing_layouts.id"), index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("process_stations.id"), index=True)
    x_pct: Mapped[float] = mapped_column(Float, default=10.0)
    y_pct: Mapped[float] = mapped_column(Float, default=10.0)
    width_pct: Mapped[float] = mapped_column(Float, default=14.0)
    height_pct: Mapped[float] = mapped_column(Float, default=12.0)
    rotation_deg: Mapped[float] = mapped_column(Float, default=0.0)
    label_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProcessAsset(Base):
    __tablename__ = "process_assets"
    __table_args__ = (UniqueConstraint("operation_id", "code", name="uq_process_asset_operation_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    operation_id: Mapped[str] = mapped_column(String(36), ForeignKey("process_operations.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    asset_type: Mapped[str] = mapped_column(String(32), default="equipment", index=True)
    asset_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calibration_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    maintenance_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProcessParameter(Base):
    __tablename__ = "process_parameters"
    __table_args__ = (UniqueConstraint("operation_id", "code", name="uq_process_parameter_operation_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    operation_id: Mapped[str] = mapped_column(String(36), ForeignKey("process_operations.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_spec_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_spec_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    special_characteristic_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("special_characteristics.id"), nullable=True, index=True)
    control_plan_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("control_plan_items.id"), nullable=True, index=True)
    measurement_method: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    reaction_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProcessDefect(Base):
    __tablename__ = "process_defects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    station_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_stations.id"), nullable=True, index=True)
    operation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_operations.id"), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    defect_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    linked_8d_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("problems_8d.id"), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LaunchReadinessItem(Base):
    """Human-owned launch/SOP readiness check linked to project/area/process evidence.

    The record is advisory evidence, not an automatic production release authority.
    """
    __tablename__ = "launch_readiness_items"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_launch_readiness_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LaunchTrial(Base):
    """Pilot build / Run@Rate / DV / PV trial evidence used by launch readiness."""
    __tablename__ = "launch_trials"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_launch_trial_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    trial_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    produced_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    good_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_rate_per_hour: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_rate_per_hour: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LocalizationItem(Base):
    """Supplier/localization readiness for one project part.

    Localization percent is an informational KPI. It never grants supplier or SOP readiness by itself.
    """
    __tablename__ = "localization_items"
    __table_args__ = (UniqueConstraint("project_code", "part_number", "supplier_code", name="uq_localization_project_part_supplier"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str] = mapped_column(String(128), index=True)
    supplier_name: Mapped[str] = mapped_column(String(512))
    source_country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    local_plant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="candidate", index=True)
    localization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_localization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_package_status: Mapped[str] = mapped_column(String(32), default="missing", index=True)
    rfq_status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    nomination_status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    tooling_status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    capacity_status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planned_sop_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class IncomingQualityRecord(Base):
    """Incoming inspection / supplier quality evidence linked to localization readiness."""
    __tablename__ = "incoming_quality_records"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_incoming_quality_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    supplier_code: Mapped[str] = mapped_column(String(128), index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lot_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    inspection_type: Mapped[str] = mapped_column(String(32), default="incoming", index=True)
    inspected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    rejected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    defect_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    acceptance_limit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    linked_8d_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("problems_8d.id"), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CostBaseline(Base):
    """Engineering cost baseline/scenario for a project.

    Cost values are advisory engineering economics. They do not replace ERP/Finance accounting
    and they never approve a sourcing or investment decision automatically.
    """
    __tablename__ = "cost_baselines"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_cost_baseline_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    baseline_type: Mapped[str] = mapped_column(String(32), default="current", index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    annual_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_vehicle_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_baseline_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cost_baselines.id"), nullable=True, index=True)
    linked_change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CostLine(Base):
    """Part-level engineering cost breakdown within a baseline/scenario."""
    __tablename__ = "cost_lines"
    __table_args__ = (UniqueConstraint("baseline_id", "part_number", "supplier_code", name="uq_cost_line_baseline_part_supplier"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    baseline_id: Mapped[str] = mapped_column(String(36), ForeignKey("cost_baselines.id"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    quantity_per_vehicle: Mapped[float] = mapped_column(Float, default=1.0)
    calculation_mode: Mapped[str] = mapped_column(String(32), default="breakdown", index=True)
    mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    material_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material_price_per_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    scrap_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    conversion_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    logistics_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    packaging_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    overhead_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    supplier_unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    other_unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    tooling_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    tooling_amortization_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SupplierQuotation(Base):
    """Supplier quotation evidence used by engineering economics."""
    __tablename__ = "supplier_quotations"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_supplier_quote_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str] = mapped_column(String(128), index=True)
    supplier_name: Mapped[str] = mapped_column(String(512))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    unit_price: Mapped[float] = mapped_column(Float)
    tooling_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringRequirement(Base):
    """Project requirement with deterministic traceability links.

    This table supports traceability and verification evidence. It does not represent
    automatic legal/OEM compliance certification.
    """
    __tablename__ = "engineering_requirements"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_requirement_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(64), default="oem", index=True)
    criticality: Mapped[str] = mapped_column(String(32), default="normal", index=True)
    title: Mapped[str] = mapped_column(String(512))
    requirement_text: Mapped[str] = mapped_column(Text)
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    source_reference: Mapped[dict] = mapped_column(JSON, default=dict)
    system_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    function_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    part_numbers: Mapped[list[str]] = mapped_column(JSON, default=list)
    special_characteristic_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    verification_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_change_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RequirementVerification(Base):
    """Verification evidence for one engineering requirement."""
    __tablename__ = "requirement_verifications"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_requirement_verification_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engineering_requirements.id"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    verification_type: Mapped[str] = mapped_column(String(64), default="test", index=True)
    phase: Mapped[str] = mapped_column(String(32), default="dv", index=True)
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    measured_result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    launch_trial_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("launch_trials.id"), nullable=True, index=True)
    design_review_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("design_reviews.id"), nullable=True, index=True)
    linked_change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    performed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requirement_updated_at_snapshot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_document_sha256_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ArchitectureNode(Base):
    """Vehicle/system architecture node. Advisory engineering structure, not a PLM authority."""
    __tablename__ = "architecture_nodes"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_architecture_node_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(512))
    node_type: Mapped[str] = mapped_column(String(32), default="component", index=True)
    parent_node_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("architecture_nodes.id"), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InterfaceDefinition(Base):
    """Controlled interface between two architecture nodes."""
    __tablename__ = "interface_definitions"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_interface_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(512))
    interface_type: Mapped[str] = mapped_column(String(32), default="mechanical", index=True)
    source_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("architecture_nodes.id"), index=True)
    target_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("architecture_nodes.id"), index=True)
    criticality: Mapped[str] = mapped_column(String(32), default="normal", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requirement_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    linked_change_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    specifications_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InterfaceVerification(Base):
    """Evidence-backed verification of an interface. A PASSED status without proof is not effective."""
    __tablename__ = "interface_verifications"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_interface_verification_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    interface_id: Mapped[str] = mapped_column(String(36), ForeignKey("interface_definitions.id"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    verification_type: Mapped[str] = mapped_column(String(32), default="review", index=True)
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    measured_result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    linked_requirement_verification_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("requirement_verifications.id"), nullable=True, index=True)
    interface_fingerprint_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    performed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class VehicleVariant(Base):
    """Named vehicle configuration/derivative. Advisory configuration layer, not PLM authority."""
    __tablename__ = "vehicle_variants"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_vehicle_variant_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    model_year: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    market: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    body_style: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    engine: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    transmission: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    trim: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_strategy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ConfigurationApplicability(Base):
    """Explicit applicability of one engineering entity to one vehicle variant. Unknown is never treated as included."""
    __tablename__ = "configuration_applicability"
    __table_args__ = (UniqueConstraint("project_code", "variant_id", "entity_type", "entity_key", name="uq_configuration_applicability"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    variant_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_variants.id"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_key: Mapped[str] = mapped_column(String(255), index=True)
    applicability: Mapped[str] = mapped_column(String(16), default="included", index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual", index=True)
    effectivity_from: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effectivity_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringLesson(Base):
    """Human-curated reusable engineering knowledge derived from a historical case.

    Historical records remain authoritative in their source tables. A lesson is a compact
    reusable summary that must be explicitly validated before the UI treats it as a
    confirmed lesson learned.
    """
    __tablename__ = "engineering_lessons"
    __table_args__ = (UniqueConstraint("project_code", "source_type", "source_id", name="uq_engineering_lesson_source"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="manual", index=True)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    problem: Mapped[str] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    effectiveness: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    validated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringDecisionRecord(Base):
    """Human-owned engineering decision with alternatives, rationale and expected outcome.

    The record is evidence/provenance. It does not replace ECR/ECO or formal approval authority.
    """
    __tablename__ = "engineering_decision_records"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_engineering_decision_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    title: Mapped[str] = mapped_column(String(512))
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    problem_statement: Mapped[str] = mapped_column(Text)
    alternatives_json: Mapped[list] = mapped_column(JSON, default=list)
    chosen_option: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_risk: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effectiveness_status: Mapped[str] = mapped_column(String(32), default="not_reviewed", index=True)
    effectiveness_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProductionFeedback(Base):
    """Observed post-change production/quality result imported or entered as evidence.

    This table stores summarized engineering feedback and never controls production equipment.
    """
    __tablename__ = "production_feedback"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_production_feedback_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    decision_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("engineering_decision_records.id"), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    observation_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observation_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    built_quantity: Mapped[int] = mapped_column(Integer, default=0)
    defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    before_defect_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    planned_cost_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    planned_mass_delta_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_mass_delta_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    planned_cycle_time_delta_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cycle_time_delta_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="observing", index=True)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChangeEffectivenessReview(Base):
    """Human-confirmed effectiveness assessment of an implemented engineering change."""
    __tablename__ = "change_effectiveness_reviews"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_change_effectiveness_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    change_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_requests.id"), index=True)
    decision_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("engineering_decision_records.id"), nullable=True, index=True)
    feedback_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("production_feedback.id"), nullable=True, index=True)
    target_description: Mapped[str] = mapped_column(Text)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="observation", index=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringDeviation(Base):
    """Time/quantity-bounded deviation/waiver evidence. Advisory; execution remains in authoritative systems."""
    __tablename__ = "engineering_deviations"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_engineering_deviation_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    released_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    quantity_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    affected_variant_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, default=list)
    approvals_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringRisk(Base):
    """Traceable engineering risk linked to part/change/supplier and mitigation evidence."""
    __tablename__ = "engineering_risks"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_engineering_risk_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    probability: Mapped[int] = mapped_column(Integer, default=1)
    severity: Mapped[int] = mapped_column(Integer, default=1)
    detectability: Mapped[int] = mapped_column(Integer, default=1)
    residual_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_detectability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mitigations_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProgramDependency(Base):
    """v5.4 deterministic engineering-program dependency between controlled milestones.

    This is not a generic task relationship. It is used only to explain schedule/gate propagation
    inside Engineering Program Control.
    """
    __tablename__ = "program_dependencies"
    __table_args__ = (UniqueConstraint("project_code", "predecessor_milestone_id", "successor_milestone_id", name="uq_program_dependency_edge"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    predecessor_milestone_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_milestones.id"), index=True)
    successor_milestone_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_milestones.id"), index=True)
    dependency_type: Mapped[str] = mapped_column(String(32), default="finish_to_start", index=True)
    lag_days: Mapped[int] = mapped_column(Integer, default=0)
    criticality: Mapped[str] = mapped_column(String(32), default="normal", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ManufacturingBOMItem(Base):
    """v5.5 manufacturing-planned product structure (MBOM) imported/read from an authoritative manufacturing source."""
    __tablename__ = "manufacturing_bom_items"
    __table_args__ = (UniqueConstraint("project_code", "variant_id", "parent_part_number", "position", "child_part_number", name="uq_mbom_item_scope"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle_variants.id"), nullable=True, index=True)
    parent_part_number: Mapped[str] = mapped_column(String(128), index=True)
    parent_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    child_part_number: Mapped[str] = mapped_column(String(128), index=True)
    child_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(32), default="pcs")
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operation_code: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_system: Mapped[str] = mapped_column(String(64), default="manual", index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ConfigurationEffectivity(Base):
    """Controlled applicability/effectivity rule. UNKNOWN is never interpreted as applicable."""
    __tablename__ = "configuration_effectivity"
    __table_args__ = (UniqueConstraint("project_code", "part_number", "revision", "variant_id", "plant", "vin_from", name="uq_configuration_effectivity_scope"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle_variants.id"), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    market: Mapped[str | None] = mapped_column(String(96), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    vin_from: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    vin_to: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    serial_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serial_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    source: Mapped[str] = mapped_column(String(64), default="manual", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChangeCutIn(Base):
    """Engineering cut-in/cutover evidence. Does not execute ERP/MES stock or VIN transactions."""
    __tablename__ = "change_cutins"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_change_cutin_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    from_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_revision: Mapped[str] = mapped_column(String(64), index=True)
    variant_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    cut_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vin_from: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    old_stock_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_stock_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_stock_disposition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    logistics_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AsBuiltConfiguration(Base):
    """Read-only/imported as-built observation used for released-vs-built assurance."""
    __tablename__ = "as_built_configuration"
    __table_args__ = (UniqueConstraint("project_code", "vehicle_identifier", "part_number", name="uq_as_built_vehicle_part"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    vehicle_identifier: Mapped[str] = mapped_column(String(128), index=True)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle_variants.id"), nullable=True, index=True)
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    built_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    deviation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("engineering_deviations.id"), nullable=True, index=True)
    source_system: Mapped[str] = mapped_column(String(64), default="import", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PartSupersession(Base):
    """Traceable part/revision supersession rule. ERP/PLM remain authoritative for execution."""
    __tablename__ = "part_supersessions"
    __table_args__ = (UniqueConstraint("project_code", "old_part_number", "old_revision", "new_part_number", "new_revision", name="uq_part_supersession"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    old_part_number: Mapped[str] = mapped_column(String(128), index=True)
    old_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_part_number: Mapped[str] = mapped_column(String(128), index=True)
    new_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    interchangeable: Mapped[bool] = mapped_column(Boolean, default=False)
    retrofit_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_use_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class VehicleBuild(Base):
    """Pilot / pre-series / safe-launch vehicle build context imported or entered for engineering analysis."""
    __tablename__ = "vehicle_builds"
    __table_args__ = (
        UniqueConstraint("project_code", "code", name="uq_vehicle_build_project_code"),
        UniqueConstraint("project_code", "vehicle_identifier", name="uq_vehicle_build_project_vehicle"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    vehicle_identifier: Mapped[str] = mapped_column(String(128), index=True)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle_variants.id"), nullable=True, index=True)
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    build_type: Mapped[str] = mapped_column(String(32), default="pilot", index=True)
    build_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    release_baseline_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("release_baselines.id"), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BuildGenealogyItem(Base):
    """VIN/build-level component genealogy. Source MES/ERP/scan remains authoritative."""
    __tablename__ = "build_genealogy_items"
    __table_args__ = (UniqueConstraint("build_id", "part_number", "serial_number", "lot_number", name="uq_build_genealogy_identity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    build_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_builds.id"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    lot_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_system: Mapped[str] = mapped_column(String(64), default="import", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BuildDefectLink(Base):
    """Links a build/VIN to an existing quality defect; never duplicates the QMS defect record."""
    __tablename__ = "build_defect_links"
    __table_args__ = (UniqueConstraint("build_id", "defect_id", name="uq_build_defect_link"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    build_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_builds.id"), index=True)
    defect_id: Mapped[str] = mapped_column(String(36), ForeignKey("process_defects.id"), index=True)
    detection_stage: Mapped[str] = mapped_column(String(64), default="build", index=True)
    containment_status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SafeLaunchControl(Base):
    """Engineering Safe Launch observation and exit criteria. Does not control inspection equipment or release production."""
    __tablename__ = "safe_launch_controls"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_safe_launch_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    characteristic: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    inspected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_clean_builds: Mapped[int] = mapped_column(Integer, default=0)
    required_clean_builds: Mapped[int] = mapped_column(Integer, default=3)
    required_inspected_quantity: Mapped[int] = mapped_column(Integer, default=100)
    exit_criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SeriesQualityObservation(Base):
    """v5.7 read-only/advisory series quality bucket imported from MES/QMS/quality sources.

    It stores aggregated factual observations only; source systems remain authoritative.
    """
    __tablename__ = "series_quality_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    station_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_stations.id"), nullable=True, index=True)
    operation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_operations.id"), nullable=True, index=True)
    shift_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle_variants.id"), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_lot: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    defect_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    characteristic: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    produced_quantity: Mapped[int] = mapped_column(Integer, default=0)
    inspected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    detected_in_process_quantity: Mapped[int] = mapped_column(Integer, default=0)
    escaped_quantity: Mapped[int] = mapped_column(Integer, default=0)
    scrap_cost: Mapped[float] = mapped_column(Float, default=0.0)
    rework_cost: Mapped[float] = mapped_column(Float, default=0.0)
    containment_cost: Mapped[float] = mapped_column(Float, default=0.0)
    warranty_cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    period_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_system: Mapped[str] = mapped_column(String(64), default="import", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcessCapabilityRecord(Base):
    """v5.7 factual process-capability snapshot. No automatic process approval is granted."""
    __tablename__ = "process_capability_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    plant: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manufacturing_lines.id"), nullable=True, index=True)
    station_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_stations.id"), nullable=True, index=True)
    operation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_operations.id"), nullable=True, index=True)
    asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("process_assets.id"), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    characteristic: Mapped[str] = mapped_column(String(512), index=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    mean_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    sigma_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_spec_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_spec_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    cp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpk: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    ppk: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source_system: Mapped[str] = mapped_column(String(64), default="import", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SeriesContainmentCase(Base):
    """v5.7 engineering containment evidence. It does not issue MES/QMS stop/release commands."""
    __tablename__ = "series_containment_cases"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_series_containment_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    title: Mapped[str] = mapped_column(String(512))
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    defect_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    supplier_lot: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    suspect_criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    suspect_vehicle_identifiers: Mapped[list[str]] = mapped_column(JSON, default=list)
    inspected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    actions_json: Mapped[list] = mapped_column(JSON, default=list)
    linked_8d_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("problems_8d.id"), nullable=True, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FieldQualityClaim(Base):
    """v5.7 field/warranty issue shadow record used only for engineering traceability."""
    __tablename__ = "field_quality_claims"
    __table_args__ = (UniqueConstraint("project_code", "claim_reference", name="uq_field_claim_project_reference"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    claim_reference: Mapped[str] = mapped_column(String(128), index=True)
    vehicle_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    failure_mode: Mapped[str] = mapped_column(String(512), index=True)
    failure_family: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    mileage_km: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    in_service_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    market: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    climate_zone: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    dealer_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    repair_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    repair_method: Mapped[str | None] = mapped_column(String(512), nullable=True)
    no_trouble_found: Mapped[bool] = mapped_column(Boolean, default=False)
    repeat_repair: Mapped[bool] = mapped_column(Boolean, default=False)
    part_cost: Mapped[float] = mapped_column(Float, default=0.0)
    labor_cost: Mapped[float] = mapped_column(Float, default=0.0)
    logistics_cost: Mapped[float] = mapped_column(Float, default=0.0)
    dealer_handling_cost: Mapped[float] = mapped_column(Float, default=0.0)
    source_system: Mapped[str] = mapped_column(String(64), default="import", index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    claim_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    linked_8d_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("problems_8d.id"), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DesignFMEAItem(Base):
    """v5.8 design-level FMEA shadow record for field-to-design feedback.

    It never changes an authoritative DFMEA automatically; review signals require human action.
    """
    __tablename__ = "design_fmea_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    function: Mapped[str | None] = mapped_column(String(512), nullable=True)
    failure_mode: Mapped[str] = mapped_column(String(512), index=True)
    effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    prevention_control: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection_control: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[int] = mapped_column(Integer, default=1)
    occurrence: Mapped[int] = mapped_column(Integer, default=1)
    detection: Mapped[int] = mapped_column(Integer, default=1)
    action_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FieldReliabilityExposure(Base):
    """v5.8 aggregated field exposure snapshot imported from warranty/fleet systems.

    Source systems remain authoritative. Censored vehicles are represented as a grouped
    right-censored population at censor_mileage_km for deterministic reliability estimates.
    """
    __tablename__ = "field_reliability_exposures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    part_number: Mapped[str] = mapped_column(String(128), index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    market: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    climate_zone: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    population_count: Mapped[int] = mapped_column(Integer, default=0)
    censored_count: Mapped[int] = mapped_column(Integer, default=0)
    censor_mileage_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_exposure_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    as_of_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source_system: Mapped[str] = mapped_column(String(64), default="import", index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FieldServiceAction(Base):
    """v5.8 engineering service/containment/campaign-assessment evidence.

    This record does not execute DMS/warranty actions and never declares a recall automatically.
    """
    __tablename__ = "field_service_actions"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_field_service_action_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    action_type: Mapped[str] = mapped_column(String(32), default="tsb", index=True)
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    failure_mode: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    safety_relevance: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    applicability_json: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    repair: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspect_vehicle_identifiers: Mapped[list[str]] = mapped_column(JSON, default=list)
    inspected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    repaired_quantity: Mapped[int] = mapped_column(Integer, default=0)
    no_defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    linked_8d_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("problems_8d.id"), nullable=True, index=True)
    linked_change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringWorkflowCase(Base):
    """v6.0 cross-domain engineering workflow orchestration record.

    The case coordinates controlled engineering work across existing domain records. It is not a
    task/project-management system of record and never grants access to evidence outside normal ACLs.
    """
    __tablename__ = "engineering_workflow_cases"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_engineering_workflow_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    workflow_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="normal", index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    current_stage: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    trigger_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trigger_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    target_gate: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    workflow_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_object_refs: Mapped[list[dict]] = mapped_column(JSON, default=list)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PilotStudy(Base):
    """v6.0.6 controlled automotive pilot definition.

    The pilot measures product/workflow outcomes, not employee performance. Participant identities,
    query text, IP addresses and viewed VIN/document history are intentionally not stored here.
    """
    __tablename__ = "pilot_studies"
    __table_args__ = (UniqueConstraint("code", name="uq_pilot_study_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(96), index=True)
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(32), default="controlled", index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    required_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    gate_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    external_gate_evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    final_decision: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    final_evaluation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PilotScenarioResult(Base):
    """Role/scenario aggregate outcome for UAT; no participant identity is persisted."""
    __tablename__ = "pilot_scenario_results"
    __table_args__ = (UniqueConstraint("pilot_id", "scenario_code", "role", name="uq_pilot_scenario_role"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pilot_id: Mapped[str] = mapped_column(String(36), ForeignKey("pilot_studies.id"), index=True)
    scenario_code: Mapped[str] = mapped_column(String(96), index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    domain: Mapped[str] = mapped_column(String(64), default="engineering", index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="not_run", index=True)
    baseline_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    mgc_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    blocker_severity: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    usability_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PilotTelemetryAggregate(Base):
    """Privacy-preserving UX aggregate. Never stores user/query/IP/VIN/document identifiers."""
    __tablename__ = "pilot_telemetry_aggregates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pilot_id: Mapped[str] = mapped_column(String(36), ForeignKey("pilot_studies.id"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    surface: Mapped[str] = mapped_column(String(96), index=True)
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    completions: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PilotUsabilityIssue(Base):
    """v6.0.7 aggregate usability issue tracked to closure.

    This record captures a workflow/interface problem, not an individual employee. It must not
    contain participant identity, raw query text, VIN/document viewing history or productivity scores.
    """
    __tablename__ = "pilot_usability_issues"
    __table_args__ = (UniqueConstraint("pilot_id", "issue_code", name="uq_pilot_usability_issue_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pilot_id: Mapped[str] = mapped_column(String(36), ForeignKey("pilot_studies.id"), index=True)
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    issue_code: Mapped[str] = mapped_column(String(96), index=True)
    role: Mapped[str] = mapped_column(String(64), default="all", index=True)
    surface: Mapped[str] = mapped_column(String(96), default="project_workspace", index=True)
    category: Mapped[str] = mapped_column(String(64), default="usability", index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    title: Mapped[str] = mapped_column(String(255))
    problem_statement: Mapped[str] = mapped_column(Text)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OperationalHealthSample(Base):
    """v6.0.8 privacy-safe component health observation for SLI/SLO trends.

    Only bounded component names, status and latency are persisted. No endpoint URL, credentials,
    user identity, VIN/part/document identifier or exception text belongs in this table.
    """
    __tablename__ = "operational_health_samples"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    component: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    detail_code: Mapped[str] = mapped_column(String(64), default="observed")


class ProductionIncident(Base):
    """v6.0.8 operator-owned incident evidence, not an engineering/QMS defect record."""
    __tablename__ = "production_incidents"
    __table_args__ = (UniqueConstraint("code", name="uq_production_incident_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(96), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    component: Mapped[str] = mapped_column(String(64), default="application", index=True)
    summary: Mapped[str] = mapped_column(String(512))
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_by: Mapped[str] = mapped_column(String(64), default="operator", index=True)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OperationsGameDayRun(Base):
    """v6.0.9 controlled operations-acceptance/game-day evidence.

    MGC records the plan, timing and evidence but never injects infrastructure faults itself.
    """
    __tablename__ = "operations_game_day_runs"
    __table_args__ = (UniqueConstraint("code", name="uq_operations_game_day_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(32), default="controlled", index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    required_exercises: Mapped[list[str]] = mapped_column(JSON, default=list)
    gate_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    external_gate_evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    final_decision: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    final_evaluation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OperationsGameDayExercise(Base):
    """One approved failure drill inside an operations game day."""
    __tablename__ = "operations_game_day_exercises"
    __table_args__ = (UniqueConstraint("run_id", "exercise_code", name="uq_operations_game_day_exercise"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("operations_game_day_runs.id"), index=True)
    exercise_code: Mapped[str] = mapped_column(String(96), index=True)
    component: Mapped[str] = mapped_column(String(64), index=True)
    scenario_type: Mapped[str] = mapped_column(String(64), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    target_rto_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_rpo_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_rpo_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fault_injected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mitigated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runbook_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ReleaseBaseline(Base):
    """Immutable engineering release snapshot. Advisory evidence record, not PLM/ERP authority."""
    __tablename__ = "release_baselines"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_release_baseline_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicle_variants.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(512))
    baseline_type: Mapped[str] = mapped_column(String(32), default="release", index=True)
    root_part_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="frozen", index=True)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    source_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    release_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# v6.3.2 — authoritative projection source + transactional outbox.
class DocumentSearchChunk(Base):
    __tablename__ = "document_search_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_search_chunk_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, index=True)
    text: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProjectionOutboxEvent(Base):
    __tablename__ = "projection_outbox_events"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_projection_outbox_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(128), index=True)
    source_version: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=8)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class ProjectionDeliveryReceipt(Base):
    __tablename__ = "projection_delivery_receipts"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_projection_delivery_receipt_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("projection_outbox_events.id", ondelete="CASCADE"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(32), index=True)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# --- v6.3.4 Engineering Revision & Conflict Management ---
class EngineeringRevisionSnapshot(Base):
    __tablename__ = "engineering_revision_snapshots"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "row_version", name="uq_revision_snapshot_entity_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    business_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    business_revision: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class WriteIdempotencyRecord(Base):
    __tablename__ = "write_idempotency_records"
    __table_args__ = (UniqueConstraint("user", "route_key", "idempotency_key", name="uq_write_idempotency_user_route_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user: Mapped[str] = mapped_column(String(255), index=True)
    route_key: Mapped[str] = mapped_column(String(255), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True)
    request_sha256: Mapped[str] = mapped_column(String(64), index=True)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EditConflictEvent(Base):
    __tablename__ = "edit_conflict_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    route: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expected_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_record_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

# --- v6.3.5 Engineering Approval & Release Governance ---
class EngineeringApprovalPolicy(Base):
    __tablename__ = "engineering_approval_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    stages_json: Mapped[list] = mapped_column(JSON, default=list)
    maker_checker_required: Mapped[bool] = mapped_column(Boolean, default=True)
    distinct_approvers_required: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringApprovalCase(Base):
    __tablename__ = "engineering_approval_cases"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "cycle_no", name="uq_approval_case_entity_cycle"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    policy_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("engineering_approval_policies.id"), nullable=True, index=True)
    policy_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    cycle_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), index=True)
    submitted_by: Mapped[str] = mapped_column(String(255), index=True)
    submitted_identity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EngineeringApprovalRecord(Base):
    __tablename__ = "engineering_approval_records"
    __table_args__ = (UniqueConstraint("case_id", "stage_key", name="uq_approval_record_case_stage"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("engineering_approval_cases.id", ondelete="CASCADE"), index=True)
    stage_key: Mapped[str] = mapped_column(String(64), index=True)
    stage_order: Mapped[int] = mapped_column(Integer)
    approver: Mapped[str] = mapped_column(String(255), index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), index=True)
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    record_hash: Mapped[str] = mapped_column(String(64), index=True)
    identity_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    assurance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EngineeringReleasePackage(Base):
    __tablename__ = "engineering_release_packages"
    __table_args__ = (UniqueConstraint("project_code", "code", name="uq_release_package_project_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": row_version}
    project_code: Mapped[str] = mapped_column(String(64), ForeignKey("projects.code"), index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(96), index=True)
    title: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    source_change_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=True, index=True)
    approval_case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("engineering_approval_cases.id"), nullable=True, index=True)
    release_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(255), index=True)
    released_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_identity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringReleasePackageItem(Base):
    __tablename__ = "engineering_release_package_items"
    __table_args__ = (UniqueConstraint("package_id", "entity_type", "entity_id", name="uq_release_package_item_entity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    package_id: Mapped[str] = mapped_column(String(36), ForeignKey("engineering_release_packages.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    business_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    business_revision: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    authority: Mapped[str] = mapped_column(String(32), default="mgc", index=True)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# --- v6.3.6 Enterprise Identity & Policy Enforcement ---
class EngineeringIdentityPolicy(Base):
    __tablename__ = "engineering_identity_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(255))
    allowed_groups_json: Mapped[list] = mapped_column(JSON, default=list)
    denied_groups_json: Mapped[list] = mapped_column(JSON, default=list)
    required_acr_values_json: Mapped[list] = mapped_column(JSON, default=list)
    require_oidc: Mapped[bool] = mapped_column(Boolean, default=False)
    max_auth_age_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allow_service_accounts: Mapped[bool] = mapped_column(Boolean, default=False)
    delegation_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringIdentityDelegation(Base):
    __tablename__ = "engineering_identity_delegations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    delegator: Mapped[str] = mapped_column(String(255), index=True)
    delegate: Mapped[str] = mapped_column(String(255), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actions_json: Mapped[list] = mapped_column(JSON, default=list)
    delegated_groups_json: Mapped[list] = mapped_column(JSON, default=list)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(255), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# --- v6.3.7 Engineering Release Handover & Integration Safety ---
class EngineeringHandoverTarget(Base):
    __tablename__ = "engineering_handover_targets"
    __table_args__ = (UniqueConstraint("code", name="uq_handover_target_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(255))
    external_system_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_systems.id"), index=True)
    environment: Mapped[str] = mapped_column(String(32), default="test", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    allow_write: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    idempotency_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    receipt_required: Mapped[bool] = mapped_column(Boolean, default=True)
    write_path: Mapped[str] = mapped_column(String(512))
    reconcile_path_template: Mapped[str | None] = mapped_column(String(512), nullable=True)
    allowed_project_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    allowed_manufacturing_areas_json: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringHandoverJob(Base):
    __tablename__ = "engineering_handover_jobs"
    __table_args__ = (UniqueConstraint("target_id", "idempotency_key", name="uq_handover_job_target_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    package_id: Mapped[str] = mapped_column(String(36), ForeignKey("engineering_release_packages.id"), index=True)
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("engineering_handover_targets.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="dry_run", index=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    manifest_sha256: Mapped[str] = mapped_column(String(64), index=True)
    request_sha256: Mapped[str] = mapped_column(String(64), index=True)
    manifest_json: Mapped[dict] = mapped_column(JSON, default=dict)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), index=True)
    maker_identity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    checker_user: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    checker_identity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    checker_assurance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    execution_identity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_receipt_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    response_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciliation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringHandoverReceipt(Base):
    __tablename__ = "engineering_handover_receipts"
    __table_args__ = (UniqueConstraint("job_id", name="uq_handover_receipt_job"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("engineering_handover_jobs.id", ondelete="CASCADE"), index=True)
    external_receipt_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="accepted", index=True)
    response_sha256: Mapped[str] = mapped_column(String(64), index=True)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    target_state_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --- v6.3.8 Data Lifecycle, Retention & Compliance Hardening ---
class EngineeringRetentionPolicy(Base):
    __tablename__ = "engineering_retention_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    archive_after_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retain_for_days: Mapped[int] = mapped_column(Integer, default=3650)
    immutable_min_days: Mapped[int] = mapped_column(Integer, default=0)
    allow_authoritative_purge: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringLegalHold(Base):
    __tablename__ = "engineering_legal_holds"
    __table_args__ = (UniqueConstraint("hold_code", name="uq_engineering_legal_hold_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hold_code: Mapped[str] = mapped_column(String(96), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    placed_by: Mapped[str] = mapped_column(String(255), index=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    released_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EngineeringDataLifecycleState(Base):
    __tablename__ = "engineering_data_lifecycle_states"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_lifecycle_state_entity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(32), default="active", index=True)
    archived_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringPurgeRequest(Base):
    __tablename__ = "engineering_purge_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    purge_scope: Mapped[str] = mapped_column(String(32), default="projections_only", index=True)
    entity_snapshot_sha256: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending_authorization", index=True)
    created_by: Mapped[str] = mapped_column(String(255), index=True)
    maker_identity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    checker_user: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    checker_identity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineeringLifecycleEvent(Base):
    __tablename__ = "engineering_lifecycle_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(96), index=True)
    actor: Mapped[str] = mapped_column(String(255), index=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

# --- v6.3.10 Cache, Read Models & Object 360 Performance ---
class EngineeringReadModel(Base):
    """Rebuildable PostgreSQL read model. Never an engineering source of truth."""
    __tablename__ = "engineering_read_models"
    __table_args__ = (UniqueConstraint("model_key", name="uq_engineering_read_model_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_key: Mapped[str] = mapped_column(String(512), index=True)
    model_type: Mapped[str] = mapped_column(String(64), index=True)
    project_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturing_area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="stale", index=True)
    source_version: Mapped[str] = mapped_column(String(64), default="", index=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
