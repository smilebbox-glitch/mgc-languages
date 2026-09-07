from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # v6.2 runtime simplification. Profiles change capability/runtime composition, never ACL.
    deployment_profile: str = "advanced"  # core | ai | advanced (advanced default preserves legacy installs)
    mgc_build_profile: str = "advanced"  # baked into container image; local source installs default to full envelope
    features_enabled: str = ""
    features_disabled: str = ""
    vector_enabled: bool = True
    app_name: str = "MGC Engineering AI Local"
    app_env: str = "dev"
    api_key: str = "change-me"
    auth_mode: str = "api_key"  # api_key | trusted_headers | oidc
    engineer_only_access: bool = True
    engineer_access_groups: str = "engineering-ai-users,engineering-ai-admins"
    engineering_admin_groups: str = "engineering-ai-admins,engineering-admin"
    api_key_groups: str = "engineering-ai-users,engineering-ai-admins"
    allow_api_key_auth_in_prod: bool = False
    trusted_user_header: str = "X-Forwarded-User"
    trusted_groups_header: str = "X-Forwarded-Groups"

    database_url: str = "sqlite:///./mgc.db"
    auto_migrate_schema: bool = True
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "engineering_chunks_v4_pilot"
    redis_url: str = "redis://localhost:6379/0"

    air_gapped_mode: bool = True
    inference_runtime: str = "gpu"  # gpu | cpu | external
    models_root: Path = Path("/models")
    docling_artifacts_path: Path = Path("/models/docling")
    local_inference_allowed_hosts: str = "model-server,vision-server,localhost,127.0.0.1,::1"
    embedding_model: str = "/models/embeddings"
    embedding_dim: int = 1024
    reranker_model: str = "/models/reranker"
    reranker_enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "change-me"
    graph_enabled: bool = False
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "mgc"
    minio_secret_key: str = "change-me"
    minio_secure: bool = False
    object_store_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""
    storage_dir: Path = Path("./storage")
    inbox_dir: Path = Path("./inbox")
    cors_origins: str = "http://localhost:3000"
    cors_methods: str = "GET,POST,PATCH,DELETE,OPTIONS"
    cors_headers: str = "Authorization,Content-Type,X-API-Key,X-Request-ID"

    llm_base_url: str = "http://model-server:8000/v1"
    llm_api_key: str = "local-only"
    llm_model: str = "mgc-local"
    llm_max_tokens: int = 1200
    llm_timeout_seconds: int = 180
    vlm_base_url: str = "http://model-server:8000/v1"
    vlm_api_key: str = "local-only"
    vlm_model: str = "mgc-local"
    vlm_timeout_seconds: int = 240

    max_upload_mb: int = 1000
    async_ingest: bool = False
    scanner_enabled: bool = True
    scanner_extensions: str = ".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.png,.jpg,.jpeg,.step,.stp,.stl,.dxf,.catpart,.catproduct,.prt,.jt,.sldprt,.sldasm,.x_t,.x_b,.m3d,.a3d,.t3d,.cdw,.frw,.spw,.kdw,.grb"
    cad_density_default_g_cm3: float | None = None
    drawing_max_pages: int = 30
    audit_retention_days: int = 3650
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_groups_claim: str = "groups"
    oidc_user_claim: str = "preferred_username"
    oidc_required: bool = False

    # v6.0.5 enterprise identity/security policy.
    oidc_allowed_algorithms: str = "RS256,RS384,RS512,ES256"
    oidc_clock_skew_seconds: int = 60
    oidc_required_claims: str = "exp,iat,sub"
    oidc_required_acr_values: str = ""
    oidc_allowed_jwks_hosts: str = ""
    allow_insecure_oidc_in_prod: bool = False
    allow_trusted_headers_in_prod: bool = False
    trusted_proxy_secret: str = ""
    audit_min_retention_days: int = 365
    audit_export_max_rows: int = 5000
    security_require_tls_edge: bool = True

    proprietary_cad_extensions: str = ".catpart,.catproduct,.prt,.jt,.sldprt,.sldasm,.x_t,.x_b,.m3d,.a3d,.t3d,.cdw,.frw,.spw,.kdw,.grb"
    integration_sync_page_limit: int = 100
    integration_sync_max_pages: int = 20
    integration_sync_enabled: bool = False
    integration_sync_interval_seconds: int = 300
    integration_sync_default_minutes: int = 15
    webhook_max_skew_seconds: int = 300

    # Production health/readiness policy. Database + evidence storage are always required.
    health_timeout_seconds: float = 2.0
    readiness_require_redis: bool = True
    readiness_require_qdrant: bool = True

    # v6.3.15 operational resilience. Breakers are process-local protection only; they never
    # become engineering truth. By default optional infrastructure does not remove Core API
    # readiness; strict legacy readiness can be re-enabled explicitly.
    resilience_enabled: bool = True
    resilience_failure_threshold: int = 3
    resilience_open_seconds: float = 30.0
    resilience_strict_dependency_readiness: bool = False

    # v6.3.16 Rolling Upgrade & Deployment Safety. Runtime component state is ephemeral
    # rollout telemetry only; PostgreSQL remains engineering truth and Redis loss never
    # authorizes an incompatible deployment. Known version/schema skew fails readiness.
    rolling_upgrade_enabled: bool = True
    rolling_upgrade_max_patch_skew: int = 1
    rolling_upgrade_task_envelope_enabled: bool = True
    rolling_upgrade_allow_legacy_task_envelopes: bool = True
    rolling_upgrade_component_registry_enabled: bool = True
    deployment_component_heartbeat_ttl_seconds: int = 120
    scheduler_leader_lock_enabled: bool = True
    scheduler_leader_retry_seconds: int = 10
    worker_drain_timeout_seconds: int = 600

    # v6.3.17 Blue/Green Cutover & Automated Rollback Safety. Stable/candidate
    # deployment state is operational metadata only; database/evidence remain authoritative.
    blue_green_enabled: bool = True
    deployment_slot: str = "stable"
    cutover_candidate_min_ready_samples: int = 3
    cutover_post_switch_samples: int = 5
    cutover_failure_threshold: int = 2
    cutover_sample_interval_seconds: int = 5
    cutover_max_patch_rollback_skew: int = 1
    cutover_state_dir: str = "/data/storage/.mgc-deployment"

    # v6.3.18 High Availability & Failover Coordination. Disabled for the simple/base
    # Compose topology; docker-compose.ha.yml enables it explicitly. Replica telemetry is
    # diagnostic and must never become engineering truth or cause a cascading Core outage.
    ha_enabled: bool = False
    ha_min_api_replicas: int = 2
    ha_min_worker_replicas_per_role: int = 2
    ha_required_worker_roles: str = "interactive,cpu,io"
    ha_require_single_scheduler_leader: bool = True
    ha_gateway_max_fails: int = 2
    ha_gateway_fail_timeout_seconds: int = 10

    # v6.3.20 Multi-host Production Topology. These labels are operational placement
    # metadata only; they never grant authorization or replace authoritative DB/evidence fencing.
    multi_host_topology_enabled: bool = False
    topology_node_id: str = ""
    topology_failure_domain: str = ""
    topology_node_role: str = "application"
    topology_min_failure_domains: int = 2
    topology_min_api_failure_domains: int = 2
    topology_min_worker_failure_domains: int = 2
    topology_required_worker_roles: str = "interactive,cpu,io"
    topology_external_lb_required: bool = True
    topology_external_lb_health_path: str = "/api/v1/health/lb"

    # v6.3.20 Database & Evidence Storage HA. Promotion/replication remain external
    # infrastructure responsibilities; MGC only opens authoritative writes when it can
    # prove it is connected to a writable PostgreSQL primary and the active evidence
    # storage generation. Disabled by default for the simple developer topology.
    authoritative_write_fence_enabled: bool = True
    database_ha_enabled: bool = False
    database_ha_require_primary_for_writes: bool = True
    database_ha_expected_system_identifier: str = ""
    evidence_ha_enabled: bool = False
    evidence_ha_mode: str = "shared"  # shared | replicated_failover
    evidence_ha_require_active_for_writes: bool = True
    evidence_ha_cluster_id: str = ""
    evidence_ha_marker_relative_path: str = ".mgc-ha/STORAGE_EPOCH.json"

    migration_lock_timeout_seconds: int = 60
    integration_sync_lock_timeout_seconds: int = 30

    # v6.0.8 observability / production support.
    operational_sampling_enabled: bool = False
    operational_sampling_interval_seconds: int = 60
    operational_health_retention_days: int = 30
    slo_dependency_availability_target: float = 0.995
    slo_integration_freshness_target: float = 0.95
    slo_queue_max_age_seconds: int = 300
    operations_default_window_minutes: int = 60
    support_bundle_max_incidents: int = 100

    # v6.3.30 Production Observability + Automated Incident Evidence. Evidence generation
    # is always read-only; optional incident materialization is explicit and never auto-resolves.
    automated_incident_materialization_enabled: bool = False

    # v6.3.21 Production Topology Certification & SLO Enforcement. SLO state gates
    # rollout/GO decisions; it does not turn a serving API into an LB outage.
    production_certification_profile: str = "30"  # 15 | 30 | 100
    db_pool_admission_control_enabled: bool = True
    db_pool_saturation_warn_ratio: float = 0.80
    db_pool_saturation_hard_ratio: float = 0.95
    db_pool_admission_retry_after_seconds: int = 3

    # v6.3.28 External Trust Anchoring & Evidence Retention Governance. The registry is
    # operational release evidence, not engineering source-of-truth data. It is disabled
    # by default and exposes only a privacy-safe summary through Engineering Admin APIs.
    release_provenance_registry_enabled: bool = False
    release_provenance_registry_path: str = "/data/storage/.mgc-release-provenance"
    release_provenance_require_external_anchor: bool = False
    release_provenance_require_worm_receipt: bool = False
    release_provenance_anchor_max_age_hours: int = 24
    release_provenance_checkpoint_max_age_hours: int = 24
    release_provenance_key_valid_days: int = 180
    release_provenance_rotation_warning_days: int = 30
    release_provenance_default_retention_days: int = 3650

    # v6.3.2 transactional outbox / rebuildable projection policy.
    projection_outbox_enabled: bool = True
    projection_worker_enabled: bool = True
    projection_worker_interval_seconds: int = 10
    projection_batch_size: int = 20
    projection_max_attempts: int = 8
    projection_retry_base_seconds: int = 5
    projection_retry_max_seconds: int = 900
    projection_lock_timeout_seconds: int = 300
    projection_lag_warning_seconds: int = 300

    # v6.3.5 approval governance. Keep legacy direct WI approval disabled by default.
    allow_legacy_direct_wi_approval: bool = False

    # v6.3.6 enterprise identity / privileged-action assurance.
    identity_policy_enforcement_enabled: bool = True
    privileged_actions_require_oidc_in_prod: bool = True
    privileged_reauth_max_age_seconds: int = 900
    privileged_required_acr_values: str = ""
    oidc_actor_type_claim: str = "actor_type"
    oidc_service_account_values: str = "service,service_account,client_credentials"
    oidc_client_id_claim: str = "azp"
    governance_postgres_rls_enabled: bool = False
    electronic_signature_mode: str = "disabled"  # disabled | external

    # v6.3.7 Engineering Release Handover & Integration Safety.
    # Read-only is the default posture: write-back requires all gates below.
    handover_write_enabled: bool = False
    handover_dry_run_default: bool = True
    handover_allowed_target_codes: str = ""
    handover_allowed_hosts: str = ""
    handover_http_timeout_seconds: int = 30
    handover_max_attempts: int = 3
    handover_reconciliation_max_age_seconds: int = 3600

    # v6.3.8 Data Lifecycle, Retention & Compliance Hardening.
    data_lifecycle_authoritative_purge_enabled: bool = False
    data_lifecycle_project_quota_mb: int = 0  # 0 = unlimited
    data_lifecycle_area_quota_mb: int = 0     # 0 = unlimited
    data_lifecycle_quota_warning_percent: int = 80
    data_lifecycle_release_retention_days: int = 3650

    # v6.3.9 Database Performance & Scale Hardening. Safe defaults measure first.
    db_pool_size: int = 15
    db_max_overflow: int = 15
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    db_slow_query_ms: float = 200.0
    db_query_budget_max_statements: int = 40
    db_query_budget_max_ms: float = 500.0
    db_query_budget_enforcement_enabled: bool = False
    cursor_page_default_limit: int = 100
    cursor_page_max_limit: int = 500
    bulk_ingest_batch_size: int = 500
    performance_scale_profile: str = "pilot_30"  # pilot_15 | pilot_30 | enterprise_100

    # v6.3.10 Cache, Read Models & Object 360 Performance. Cache is acceleration only.
    read_model_enabled: bool = True
    read_model_cache_enabled: bool = True
    read_model_cache_ttl_seconds: int = 60
    read_model_pending_invalidation_bypass: bool = True
    object360_cache_ttl_seconds: int = 30

    # v6.3.11 Background Jobs, Scheduler & Workload Isolation.
    # Heavy work is isolated by resource class; Core never requires an AI/GPU worker.
    job_project_default_concurrency: int = 2
    job_project_cad_concurrency: int = 1
    job_project_ai_concurrency: int = 1
    job_max_attempts_cap: int = 8
    job_retry_base_seconds: int = 15
    job_retry_max_seconds: int = 900
    job_cancel_revoke_enabled: bool = True
    job_worker_heartbeat_warning_seconds: int = 300
    # v6.3.13 lease/fencing recovery. Lease duration is task timeout + grace; only
    # explicitly replay-safe job kinds may be auto-requeued after lease expiry.
    job_worker_lease_grace_seconds: int = 120
    job_auto_recovery_enabled: bool = True
    job_auto_recovery_max_per_cycle: int = 25
    job_scheduler_enabled: bool = True
    job_scheduler_interval_seconds: int = 60
    object360_max_section_items: int = 500
    digital_thread_default_max_nodes: int = 280
    digital_thread_hard_max_nodes: int = 500

    @property
    def handover_allowed_host_set(self) -> set[str]:
        return {x.strip().lower() for x in self.handover_allowed_hosts.split(",") if x.strip()}

    @property
    def handover_allowed_target_code_set(self) -> set[str]:
        return {x.strip().lower() for x in self.handover_allowed_target_codes.split(",") if x.strip()}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


    @property
    def runtime_profile(self) -> str:
        from app.core.runtime_contract import normalize_profile
        return normalize_profile(self.deployment_profile)

    @property
    def runtime_features(self) -> set[str]:
        from app.core.runtime_contract import resolved_features
        return resolved_features(self.runtime_profile, self.features_enabled, self.features_disabled)

    @property
    def semantic_search_enabled(self) -> bool:
        return bool(self.vector_enabled and "qdrant" in self.runtime_features and "semantic_search" in self.runtime_features)

    @property
    def runtime_qdrant_required(self) -> bool:
        return bool(self.readiness_require_qdrant and self.semantic_search_enabled)

    @property
    def runtime_graph_enabled(self) -> bool:
        return bool(self.graph_enabled and "neo4j_projection" in self.runtime_features)

    @property
    def runtime_object_store_enabled(self) -> bool:
        return bool(self.object_store_enabled and "object_store" in self.runtime_features)

    @property
    def cors_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


    @property
    def cors_method_list(self) -> list[str]:
        return [x.strip().upper() for x in self.cors_methods.split(",") if x.strip()]

    @property
    def cors_header_list(self) -> list[str]:
        return [x.strip() for x in self.cors_headers.split(",") if x.strip()]

    @property
    def local_inference_allowed_host_set(self) -> set[str]:
        return {x.strip().lower() for x in self.local_inference_allowed_hosts.split(",") if x.strip()}

    @property
    def scanner_extension_set(self) -> set[str]:
        return {x.strip().lower() for x in self.scanner_extensions.split(",") if x.strip()}

    @property
    def proprietary_cad_extension_set(self) -> set[str]:
        return {x.strip().lower() for x in self.proprietary_cad_extensions.split(",") if x.strip()}

    @property
    def engineer_access_group_set(self) -> set[str]:
        return {x.strip() for x in self.engineer_access_groups.split(",") if x.strip()}

    @property
    def engineering_admin_group_set(self) -> set[str]:
        return {x.strip() for x in self.engineering_admin_groups.split(",") if x.strip()}

    @property
    def api_key_group_set(self) -> set[str]:
        return {x.strip() for x in self.api_key_groups.split(",") if x.strip()}

    @property
    def oidc_allowed_algorithm_set(self) -> set[str]:
        return {x.strip() for x in self.oidc_allowed_algorithms.split(",") if x.strip()}

    @property
    def oidc_required_claim_set(self) -> set[str]:
        return {x.strip() for x in self.oidc_required_claims.split(",") if x.strip()}

    @property
    def oidc_required_acr_set(self) -> set[str]:
        return {x.strip() for x in self.oidc_required_acr_values.split(",") if x.strip()}

    @property
    def oidc_allowed_jwks_host_set(self) -> set[str]:
        return {x.strip().lower() for x in self.oidc_allowed_jwks_hosts.split(",") if x.strip()}

    @property
    def privileged_required_acr_set(self) -> set[str]:
        return {x.strip() for x in self.privileged_required_acr_values.split(",") if x.strip()}

    @property
    def oidc_service_account_value_set(self) -> set[str]:
        return {x.strip().lower() for x in self.oidc_service_account_values.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    s.inbox_dir.mkdir(parents=True, exist_ok=True)
    return s
