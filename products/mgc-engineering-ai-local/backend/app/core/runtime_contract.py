from __future__ import annotations

from typing import Iterable

APP_VERSION = "6.3.34"
# v6.3.34 standardizes passenger/commercial vehicle classes and configuration applicability without changing the automotive database schema.
# No automotive-domain schema change; v6.3.13 remains the current database schema.
SCHEMA_VERSION = "6.3.13"
RUNTIME_SCHEMA = "mgc-runtime-contract-v1"

# Six bounded contexts replace feature-by-feature architecture as the primary mental model.
BOUNDED_CONTEXTS: dict[str, dict] = {
    "engineering_core": {
        "label": "Engineering Core",
        "owns": ["project", "part", "document", "requirement", "drawing", "cad", "relationship"],
    },
    "configuration_change": {
        "label": "Configuration & Change",
        "owns": ["bom", "revision", "effectivity", "ecr_eco", "release", "change_impact"],
    },
    "manufacturing_quality": {
        "label": "Manufacturing & Quality",
        "owns": ["process", "station", "work_instruction", "layout", "build", "vin", "genealogy", "pfmea", "control_plan", "defect", "series_quality"],
    },
    "supplier_field": {
        "label": "Supplier & Field",
        "owns": ["supplier", "ppap", "run_at_rate", "8d", "warranty", "field_reliability"],
    },
    "intelligence_search": {
        "label": "Intelligence & Search",
        "owns": ["search", "rag", "engineering_memory", "analytics", "explanations"],
    },
    "platform_operations": {
        "label": "Platform & Operations",
        "owns": ["auth", "acl", "audit", "evidence", "actions", "workflows", "integrations", "operations"],
    },
}

# Profiles are additive capability envelopes, not authorization policies.
PROFILE_FEATURES: dict[str, set[str]] = {
    "core": {
        "postgres_core", "redis_jobs", "local_evidence_storage", "lexical_search",
        "engineering_core", "configuration_change", "manufacturing_quality",
        "platform_operations", "object360", "actions", "evidence", "connectors",
    },
    "ai": {
        "postgres_core", "redis_jobs", "local_evidence_storage", "lexical_search",
        "engineering_core", "configuration_change", "manufacturing_quality",
        "platform_operations", "object360", "actions", "evidence", "connectors",
        "qdrant", "semantic_search", "embeddings", "reranker", "local_llm", "local_vlm",
        "intelligence_search",
    },
    "advanced": {
        "postgres_core", "redis_jobs", "local_evidence_storage", "lexical_search",
        "engineering_core", "configuration_change", "manufacturing_quality", "supplier_field",
        "platform_operations", "object360", "actions", "evidence", "connectors",
        "qdrant", "semantic_search", "embeddings", "reranker", "local_llm", "local_vlm",
        "intelligence_search", "neo4j_projection", "object_store", "native_cad_gateway",
        "advanced_field", "cost_economics", "program_control",
    },
}

PROFILE_DESCRIPTIONS = {
    "core": "Deterministic engineering core. PostgreSQL + Redis + local evidence storage; no vector DB, graph DB or model server required.",
    "ai": "Recommended pilot profile. Core plus Qdrant and local AI/search enrichment.",
    "advanced": "Full capability envelope. AI plus optional graph projection, object store, native CAD and advanced lifecycle domains.",
}
PROFILE_ALIASES = {"core_only": "core", "core+ai": "ai", "core_ai": "ai", "full": "advanced"}
PROFILE_RANK = {"core": 0, "ai": 1, "advanced": 2}
CORE_INVARIANTS = {"postgres_core", "local_evidence_storage", "platform_operations", "evidence"}
ALL_FEATURES = frozenset().union(*PROFILE_FEATURES.values())

# Object 360 is profile-aware. A type can be shown only when its owning capability is active.
OBJECT_TYPE_CAPABILITIES: dict[str, str] = {
    "part": "engineering_core",
    "vin": "manufacturing_quality",
    "change": "configuration_change",
    "defect": "manufacturing_quality",
    "requirement": "engineering_core",
    "supplier": "supplier_field",
}

CAPABILITY_CONTEXTS: dict[str, str] = {
    "engineering_core": "engineering_core",
    "configuration_change": "configuration_change",
    "manufacturing_quality": "manufacturing_quality",
    "supplier_field": "supplier_field",
    "intelligence_search": "intelligence_search",
    "platform_operations": "platform_operations",
    "object360": "platform_operations",
    "actions": "platform_operations",
    "evidence": "platform_operations",
    "connectors": "platform_operations",
    "lexical_search": "intelligence_search",
    "semantic_search": "intelligence_search",
    "embeddings": "intelligence_search",
    "reranker": "intelligence_search",
    "local_llm": "intelligence_search",
    "local_vlm": "intelligence_search",
    "qdrant": "intelligence_search",
    "neo4j_projection": "intelligence_search",
    "native_cad_gateway": "engineering_core",
    "advanced_field": "supplier_field",
    "cost_economics": "configuration_change",
    "program_control": "platform_operations",
    "postgres_core": "platform_operations",
    "redis_jobs": "platform_operations",
    "local_evidence_storage": "platform_operations",
    "object_store": "platform_operations",
}


class RuntimeConfigurationError(ValueError):
    """Deployment-profile configuration is contradictory or would widen the selected profile."""


def normalize_profile(value: str | None, *, strict: bool = True) -> str:
    raw = (value or "advanced").strip().lower()
    raw = PROFILE_ALIASES.get(raw, raw)
    if raw in PROFILE_FEATURES:
        return raw
    if strict:
        raise RuntimeConfigurationError(
            f"Unknown DEPLOYMENT_PROFILE '{value}'. Expected one of: core, ai, advanced."
        )
    # Diagnostic callers may request a safe fallback; never fail open to Advanced.
    return "core"


def parse_feature_list(value: str | Iterable[str] | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {x.strip().lower() for x in value.split(",") if x.strip()}
    return {str(x).strip().lower() for x in value if str(x).strip()}


def validate_feature_overrides(profile: str, enabled: str | Iterable[str] | None = None, disabled: str | Iterable[str] | None = None) -> dict:
    resolved_profile = normalize_profile(profile)
    allowed = PROFILE_FEATURES[resolved_profile]
    enable_set = parse_feature_list(enabled)
    disable_set = parse_feature_list(disabled)
    unknown = (enable_set | disable_set) - ALL_FEATURES
    escalation = enable_set - allowed
    errors: list[str] = []
    warnings: list[str] = []
    if unknown:
        errors.append(f"Unknown runtime features: {', '.join(sorted(unknown))}")
    if escalation:
        errors.append(
            f"Profile '{resolved_profile}' cannot enable higher-profile capabilities: {', '.join(sorted(escalation))}. "
            "Select ai/advanced instead of widening a lower profile with feature flags."
        )
    ignored_core_disables = disable_set & CORE_INVARIANTS
    if ignored_core_disables:
        warnings.append(f"Core invariants cannot be disabled: {', '.join(sorted(ignored_core_disables))}")
    if enable_set:
        warnings.append("FEATURES_ENABLED is retained for compatibility but cannot widen the selected deployment profile.")
    return {
        "valid": not errors,
        "profile": resolved_profile,
        "enabled": sorted(enable_set),
        "disabled": sorted(disable_set),
        "errors": errors,
        "warnings": warnings,
        "ignored_core_disables": sorted(ignored_core_disables),
    }


def resolved_features(profile: str, enabled: str | Iterable[str] | None = None, disabled: str | Iterable[str] | None = None) -> set[str]:
    diagnostics = validate_feature_overrides(profile, enabled, disabled)
    if diagnostics["errors"]:
        raise RuntimeConfigurationError("; ".join(diagnostics["errors"]))
    features = set(PROFILE_FEATURES[diagnostics["profile"]])
    # FEATURES_ENABLED can re-assert only capabilities already inside the selected profile.
    features |= set(diagnostics["enabled"])
    features -= set(diagnostics["disabled"])
    # Core invariants may not be disabled by feature flags.
    features |= CORE_INVARIANTS
    return features


def feature_enabled(profile: str, feature: str, enabled: str | Iterable[str] | None = None, disabled: str | Iterable[str] | None = None) -> bool:
    return feature.strip().lower() in resolved_features(profile, enabled, disabled)


def context_for_capability(capability: str) -> str | None:
    c = capability.strip().lower()
    if c in CAPABILITY_CONTEXTS:
        return CAPABILITY_CONTEXTS[c]
    for code, meta in BOUNDED_CONTEXTS.items():
        if c in set(meta["owns"]):
            return code
    return None


def available_object_types(features: Iterable[str]) -> list[str]:
    active = {str(x).strip().lower() for x in features}
    return sorted(kind for kind, capability in OBJECT_TYPE_CAPABILITIES.items() if capability in active and "object360" in active)


def active_bounded_contexts(features: Iterable[str]) -> list[str]:
    """Return contexts that own at least one active runtime capability.

    Context composition is a runtime-surface decision, never an authorization grant.
    Core retains Intelligence & Search because lexical_search is active even when the
    semantic/LLM capabilities are absent. Supplier & Field is omitted unless one of
    its capabilities is present.
    """
    active = {str(x).strip().lower() for x in features}
    contexts = set()
    for capability in active:
        context = context_for_capability(capability)
        if context:
            contexts.add(context)
    return [code for code in BOUNDED_CONTEXTS if code in contexts]


def validate_build_profile(runtime_profile: str, build_profile: str | None) -> dict:
    runtime = normalize_profile(runtime_profile)
    build = normalize_profile(build_profile or "advanced")
    compatible = PROFILE_RANK[build] >= PROFILE_RANK[runtime]
    if not compatible:
        raise RuntimeConfigurationError(
            f"Runtime profile '{runtime}' requires an image built for '{runtime}' or higher; "
            f"current image dependency envelope is '{build}'. Rebuild with DEPLOYMENT_PROFILE={runtime}."
        )
    return {"runtime_profile": runtime, "build_profile": build, "compatible": True}


def runtime_contract(settings) -> dict:
    requested_profile = getattr(settings, "deployment_profile", "advanced")
    profile = normalize_profile(requested_profile)
    build_compatibility = validate_build_profile(profile, getattr(settings, "mgc_build_profile", "advanced"))
    enabled = getattr(settings, "features_enabled", "")
    disabled = getattr(settings, "features_disabled", "")
    diagnostics = validate_feature_overrides(profile, enabled, disabled)
    if diagnostics["errors"]:
        raise RuntimeConfigurationError("; ".join(diagnostics["errors"]))
    features = resolved_features(profile, enabled, disabled)
    from app.adapters.registry import adapter_contract
    adapters = adapter_contract(settings)
    dependencies = {
        "postgres": {"required": True, "role": "authoritative platform store"},
        "redis": {"required": "redis_jobs" in features, "core_readiness_required": False, "role": "transient jobs/queue; job execution degrades while synchronous engineering core remains available"},
        "qdrant": {"required": "qdrant" in features, "core_readiness_required": False, "role": "rebuildable semantic-search projection with lexical fallback"},
        "neo4j": {"required": "neo4j_projection" in features and bool(getattr(settings, "graph_enabled", False)), "role": "optional rebuildable graph projection"},
        "object_store": {"required": "object_store" in features and bool(getattr(settings, "object_store_enabled", False)), "role": "optional evidence object storage"},
        "local_ai": {"required": False, "role": "optional explanation/search enrichment"},
    }
    return {
        "schema": RUNTIME_SCHEMA,
        "version": APP_VERSION,
        "profile": profile,
        "requested_profile": str(requested_profile),
        "profile_description": PROFILE_DESCRIPTIONS[profile],
        "features": sorted(features),
        "bounded_contexts": [{"code": k, **v} for k, v in BOUNDED_CONTEXTS.items()],
        "active_bounded_contexts": active_bounded_contexts(features),
        "schema_version": SCHEMA_VERSION,
        "capability_contexts": {feature: context_for_capability(feature) for feature in sorted(features)},
        "object360": {
            "available_types": available_object_types(features),
            "type_capabilities": OBJECT_TYPE_CAPABILITIES,
            "conditional_get": True,
            "acl_scoped_acceleration_cache": bool(getattr(settings, "read_model_cache_enabled", True)),
        },
        "read_models": {
            "enabled": bool(getattr(settings, "read_model_enabled", True)),
            "authoritative": False,
            "rebuildable": True,
            "redis_required_for_correctness": False,
            "pending_invalidation_bypasses_cache": bool(getattr(settings, "read_model_pending_invalidation_bypass", True)),
        },
        "rolling_upgrade": {
            "enabled": bool(getattr(settings, "rolling_upgrade_enabled", True)),
            "same_schema_required": True,
            "max_patch_skew": int(getattr(settings, "rolling_upgrade_max_patch_skew", 1)),
            "task_envelope_fencing": bool(getattr(settings, "rolling_upgrade_task_envelope_enabled", True)),
            "component_registry_authoritative": False,
            "worker_drain_required": True,
            "scheduler_single_leader_required": True,
        },
        "high_availability": {
            "enabled": bool(getattr(settings, "ha_enabled", False)),
            "minimum_api_replicas": int(getattr(settings, "ha_min_api_replicas", 2)),
            "minimum_worker_replicas_per_role": int(getattr(settings, "ha_min_worker_replicas_per_role", 2)),
            "required_worker_roles": str(getattr(settings, "ha_required_worker_roles", "interactive,cpu,io")),
            "passive_gateway_failover": True,
            "non_idempotent_gateway_retry": False,
            "cluster_telemetry_authoritative": False,
        },
        "authoritative_data_ha": {
            "database_ha_enabled": bool(getattr(settings, "database_ha_enabled", False)),
            "evidence_ha_enabled": bool(getattr(settings, "evidence_ha_enabled", False)),
            "authoritative_write_fence": bool(getattr(settings, "authoritative_write_fence_enabled", True)),
            "postgresql_primary_required_for_mutation": True,
            "evidence_active_generation_required_for_mutation": True,
            "external_failover_manager_required": True,
            "external_stonith_required": True,
            "application_promotes_postgresql": False,
        },
        "production_certification": {
            "profile": str(getattr(settings, "production_certification_profile", "30")),
            "slo_failure_blocks_existing_lb_readiness": False,
            "slo_failure_blocks_new_rollout": True,
            "db_pool_admission_control_enabled": bool(getattr(settings, "db_pool_admission_control_enabled", True)),
            "db_pool_saturation_warn_ratio": float(getattr(settings, "db_pool_saturation_warn_ratio", 0.80)),
            "db_pool_saturation_hard_ratio": float(getattr(settings, "db_pool_saturation_hard_ratio", 0.95)),
            "target_host_evidence_required_for_go": True,
            "human_change_approval_required": True,
            "packaging_environment_can_issue_production_go": False,
        },
        "configuration": diagnostics,
        "build_compatibility": build_compatibility,
        "dependencies": dependencies,
        "adapters": adapters,
        "data_classes": {
            "authoritative_external": ["PLM/PDM", "ERP", "MES", "QMS"],
            "mgc_authoritative": ["workflow", "decision", "mapping_confirmation", "pilot", "incident"],
            "derived_rebuildable": ["embeddings", "vector_index", "graph_projection", "risk_signal", "summary", "read_model", "acceleration_cache"],
        },
        "governance": {
            "profile_is_not_authorization": True,
            "profile_cannot_be_widened_by_feature_flags": True,
            "invalid_profile_fails_closed": True,
            "postgres_is_core_store": True,
            "derived_stores_are_rebuildable": True,
            "legacy_api_compatibility": True,
            "dependency_inversion": True,
            "graceful_optional_dependency_degradation": True,
            "process_local_circuit_breakers_non_authoritative": True,
            "transactional_outbox": True,
            "rebuildable_projections": True,
            "read_models_non_authoritative": True,
            "redis_cache_non_authoritative": True,
            "optimistic_concurrency": True,
            "domain_unit_of_work": True,
            "db_domain_constraints": True,
            "advanced_technology_behind_ports": True,
        },
    }
