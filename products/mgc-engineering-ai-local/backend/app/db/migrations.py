from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _add_missing_columns(engine: Engine, table: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in set(inspector.get_table_names()):
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def ensure_v40_schema(engine: Engine) -> None:
    """Additive/idempotent upgrade path from v3.4-v3.9 pilot databases."""
    _add_missing_columns(engine, "design_reviews", {"report_json": "JSON"})
    _add_missing_columns(engine, "documents", {"manufacturing_area": "VARCHAR(64)"})
    _add_missing_columns(engine, "project_milestones", {"manufacturing_area": "VARCHAR(64)"})

    _add_missing_columns(engine, "projects", {
        "description": "TEXT",
        "status": "VARCHAR(32) DEFAULT 'active'",
        "phase": "VARCHAR(64) DEFAULT 'development'",
        "owner": "VARCHAR(255)",
        "root_part_number": "VARCHAR(128)",
        "target_release_at": "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME",
        "metadata_json": "JSON",
        "updated_at": "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME",
    })
    if "projects" in set(inspect(engine).get_table_names()):
        with engine.begin() as conn:
            conn.execute(text("UPDATE projects SET status='active' WHERE status IS NULL OR status=''"))
            conn.execute(text("UPDATE projects SET phase='development' WHERE phase IS NULL OR phase=''"))
    _add_missing_columns(engine, "change_requests", {
        "eco_code": "VARCHAR(128)",
        "reason": "TEXT",
        "priority": "VARCHAR(32) DEFAULT 'normal'",
        "owner": "VARCHAR(255)",
        "created_by": "VARCHAR(255) DEFAULT 'system'",
        "impact_json": "JSON",
        "affected_parts": "JSON",
        "affected_document_ids": "JSON",
        "design_review_id": "VARCHAR(36)",
        "implementation_plan": "JSON",
        "verification_plan": "JSON",
        "completed_at": "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME",
    })
    if "change_requests" in set(inspect(engine).get_table_names()):
        with engine.begin() as conn:
            conn.execute(text("UPDATE change_requests SET status='draft' WHERE status='open'"))
            conn.execute(text("UPDATE change_requests SET priority='normal' WHERE priority IS NULL OR priority=''"))
            conn.execute(text("UPDATE change_requests SET created_by='system' WHERE created_by IS NULL OR created_by=''"))


# Backward-compatible import name used by older scripts/tests.
def ensure_v39_schema(engine: Engine) -> None:
    ensure_v40_schema(engine)


def ensure_v38_schema(engine: Engine) -> None:
    ensure_v40_schema(engine)


def ensure_v35_schema(engine: Engine) -> None:
    ensure_v40_schema(engine)


def ensure_v41_schema(engine: Engine) -> None:
    """v4.1 adds new Core Tools tables via SQLAlchemy create_all; keep additive legacy upgrades."""
    ensure_v40_schema(engine)


def ensure_v42_schema(engine: Engine) -> None:
    """v4.2 adds Process Digital Thread tables and stable PFMEA/Control Plan operation links."""
    ensure_v41_schema(engine)
    _add_missing_columns(engine, "pfmea_items", {"process_operation_id": "VARCHAR(36)"})
    _add_missing_columns(engine, "control_plan_items", {"process_operation_id": "VARCHAR(36)"})


def ensure_v43_schema(engine: Engine) -> None:
    """v4.3 adds Launch & Plant Readiness tables through SQLAlchemy create_all."""
    ensure_v42_schema(engine)


def ensure_v44_schema(engine: Engine) -> None:
    """v4.4 adds Requirements & Verification Matrix tables through SQLAlchemy create_all."""
    ensure_v43_schema(engine)


def ensure_v45_schema(engine: Engine) -> None:
    """v4.5 adds Supplier & Localization Engineering tables through SQLAlchemy create_all."""
    ensure_v44_schema(engine)


def ensure_v46_schema(engine: Engine) -> None:
    """v4.6 adds Cost & Engineering Economics tables through SQLAlchemy create_all."""
    ensure_v45_schema(engine)


def ensure_v47_schema(engine: Engine) -> None:
    """v4.7 adds Vehicle/System Architecture & Interface Management tables via create_all."""
    ensure_v46_schema(engine)


def ensure_v48_schema(engine: Engine) -> None:
    """v4.8 adds Vehicle Variant & Configuration Management tables via create_all."""
    ensure_v47_schema(engine)


def ensure_v49_schema(engine: Engine) -> None:
    """v4.9 adds immutable release baselines and richer BOM comparison fields."""
    ensure_v48_schema(engine)
    _add_missing_columns(engine, "bom_items", {
        "position": "VARCHAR(64)",
        "supplier_code": "VARCHAR(128)",
        "supplier_name": "VARCHAR(512)",
        "unit_cost": "FLOAT",
        "currency": "VARCHAR(3)",
    })


def ensure_v52_schema(engine: Engine) -> None:
    """v5.2 adds Engineering Knowledge Memory lesson storage via SQLAlchemy create_all.

    The wrapper is intentionally additive/idempotent and preserves all previous schema
    upgrade behavior for existing pilot databases.
    """
    ensure_v49_schema(engine)


def ensure_v53_schema(engine: Engine) -> None:
    """v5.3 adds Closed-Loop Engineering Intelligence tables via SQLAlchemy create_all.

    The wrapper is additive/idempotent; existing v5.2 and older pilot schemas are preserved.
    """
    ensure_v52_schema(engine)


def ensure_v54_schema(engine: Engine) -> None:
    """v5.4 adds Engineering Program Control dependency storage via SQLAlchemy create_all.

    All program maturity, forecast and command-center outputs are derived from existing controlled
    engineering records plus this additive dependency graph.
    """
    ensure_v53_schema(engine)


def ensure_v55_schema(engine: Engine) -> None:
    """v5.5 adds Configuration & Release Assurance tables via SQLAlchemy create_all.

    The wrapper remains additive/idempotent; existing v5.4 and older pilot databases are preserved.
    """
    ensure_v54_schema(engine)


def ensure_v56_schema(engine: Engine) -> None:
    """v5.6 adds Vehicle Build & Launch Intelligence tables via SQLAlchemy create_all.

    The wrapper is additive/idempotent and preserves all v5.5 configuration/release assurance data.
    """
    ensure_v55_schema(engine)


def ensure_v57_schema(engine: Engine) -> None:
    """v5.7 adds Series Quality & Manufacturing Intelligence tables via SQLAlchemy create_all.

    The wrapper is additive/idempotent and preserves v5.6 build/genealogy data.
    """
    ensure_v56_schema(engine)


def ensure_v58_schema(engine: Engine) -> None:
    """v5.8 adds Field Reliability & Product Lifecycle Intelligence tables/columns.

    Additive/idempotent wrapper. Existing v5.7 field claims gain optional lifecycle fields;
    new DFMEA/exposure/service-action tables are created through SQLAlchemy create_all.
    """
    ensure_v57_schema(engine)
    _add_missing_columns(engine, "field_quality_claims", {
        "failure_family": "VARCHAR(255)",
        "mileage_km": "FLOAT",
        "in_service_at": "DATETIME",
        "market": "VARCHAR(96)",
        "climate_zone": "VARCHAR(96)",
        "dealer_code": "VARCHAR(128)",
        "repair_code": "VARCHAR(128)",
        "repair_method": "VARCHAR(512)",
        "no_trouble_found": "BOOLEAN DEFAULT 0",
        "repeat_repair": "BOOLEAN DEFAULT 0",
        "part_cost": "FLOAT DEFAULT 0",
        "labor_cost": "FLOAT DEFAULT 0",
        "logistics_cost": "FLOAT DEFAULT 0",
        "dealer_handling_cost": "FLOAT DEFAULT 0",
        "source_system": "VARCHAR(64) DEFAULT 'import'",
    })


def ensure_v60_schema(engine: Engine) -> None:
    """v6.0 adds Engineering Intelligence OS workflow orchestration storage.

    Role cockpit/action inbox are derived from existing controlled records; only cross-domain
    workflow cases need additive persistence through SQLAlchemy create_all.
    """
    ensure_v58_schema(engine)


def ensure_v601_schema(engine: Engine) -> None:
    """v6.0.1 Production Hardening schema-state marker.

    No business-domain schema is changed. The marker lets readiness fail closed when a
    deployment starts against a database whose startup migration did not complete.
    """
    ensure_v60_schema(engine)
    timestamp_type = "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME"
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS mgc_schema_state ("
            "id INTEGER PRIMARY KEY, schema_version VARCHAR(32) NOT NULL, applied_at " + timestamp_type + " NOT NULL)"
        ))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.1', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.1', CURRENT_TIMESTAMP)"))


def ensure_v602_schema(engine: Engine) -> None:
    """v6.0.2 Integration Hardening & Data Confidence.

    Adds provenance/contract/quality columns to the existing integration fabric. The
    integration_ingest_events ledger itself is created by SQLAlchemy create_all. All
    changes are additive and idempotent for existing v6.0.1 pilot databases.
    """
    ensure_v601_schema(engine)
    timestamp_type = "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME"
    _add_missing_columns(engine, "external_systems", {
        "source_domain": "VARCHAR(32) DEFAULT 'engineering'",
        "contract_version": "VARCHAR(64) DEFAULT 'mgc-integration-v1'",
        "expected_freshness_minutes": "INTEGER",
        "required_fields": "JSON",
        "last_quality_json": "JSON",
        "last_quality_at": timestamp_type,
    })
    _add_missing_columns(engine, "external_objects", {
        "source_modified_at": timestamp_type,
        "data_confidence_score": "FLOAT",
        "data_confidence_level": "VARCHAR(16)",
        "data_quality_json": "JSON",
    })
    _add_missing_columns(engine, "integration_runs", {
        "quarantined_count": "INTEGER DEFAULT 0",
        "replayed_count": "INTEGER DEFAULT 0",
        "quality_json": "JSON",
    })
    with engine.begin() as conn:
        conn.execute(text("UPDATE external_systems SET source_domain='engineering' WHERE source_domain IS NULL OR source_domain=''"))
        conn.execute(text("UPDATE external_systems SET contract_version='mgc-integration-v1' WHERE contract_version IS NULL OR contract_version=''"))
        conn.execute(text("UPDATE external_systems SET required_fields='[]' WHERE required_fields IS NULL") if engine.dialect.name == "sqlite" else text("UPDATE external_systems SET required_fields='[]'::json WHERE required_fields IS NULL"))
        conn.execute(text("UPDATE external_systems SET last_quality_json='{}' WHERE last_quality_json IS NULL") if engine.dialect.name == "sqlite" else text("UPDATE external_systems SET last_quality_json='{}'::json WHERE last_quality_json IS NULL"))
        conn.execute(text("UPDATE external_objects SET data_quality_json='{}' WHERE data_quality_json IS NULL") if engine.dialect.name == "sqlite" else text("UPDATE external_objects SET data_quality_json='{}'::json WHERE data_quality_json IS NULL"))
        conn.execute(text("UPDATE integration_runs SET quarantined_count=0 WHERE quarantined_count IS NULL"))
        conn.execute(text("UPDATE integration_runs SET replayed_count=0 WHERE replayed_count IS NULL"))
        conn.execute(text("UPDATE integration_runs SET quality_json='{}' WHERE quality_json IS NULL") if engine.dialect.name == "sqlite" else text("UPDATE integration_runs SET quality_json='{}'::json WHERE quality_json IS NULL"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.2', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.2', CURRENT_TIMESTAMP)"))


def ensure_v603_schema(engine: Engine) -> None:
    """v6.0.3 Real Integration Pilot & Data Reconciliation.

    The canonical mapping registry is created through SQLAlchemy create_all. Reconciliation
    reports remain derived from current external objects and controlled engineering records.
    No authoritative PLM/ERP/MES/QMS data is copied into a second domain model.
    """
    ensure_v602_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.3', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.3', CURRENT_TIMESTAMP)"))


def ensure_v604_schema(engine: Engine) -> None:
    """v6.0.4 Performance, Scale & Load Certification.

    Adds only composite indexes for high-cardinality engineering read paths. No business-domain
    ownership or data semantics change. Index creation is additive/idempotent and portable across
    supported PostgreSQL/SQLite pilot environments.
    """
    ensure_v603_schema(engine)
    indexes = [
        ("idx_v604_bom_parent_revision_child", "bom_items", "parent_part_number, parent_revision, child_part_number"),
        ("idx_v604_relationship_subject_predicate", "relationships", "subject_type, subject_id, predicate"),
        ("idx_v604_relationship_object_predicate", "relationships", "object_type, object_id, predicate"),
        ("idx_v604_vehicle_build_project_vin_status", "vehicle_builds", "project_code, vehicle_identifier, status"),
        ("idx_v604_genealogy_build_part_supplier_lot", "build_genealogy_items", "build_id, part_number, supplier_code, lot_number"),
        ("idx_v604_series_project_time_part", "series_quality_observations", "project_code, observed_at, part_number"),
        ("idx_v604_external_object_system_type_part", "external_objects", "system_id, object_type, part_number"),
        ("idx_v604_ingest_system_status_received", "integration_ingest_events", "system_id, status, first_received_at"),
        ("idx_v604_mapping_project_type_status", "integration_entity_mappings", "project_code, canonical_entity_type, status"),
    ]
    existing_tables = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        for name, table, columns in indexes:
            if table in existing_tables:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.4', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.4', CURRENT_TIMESTAMP)"))


def ensure_v605_schema(engine: Engine) -> None:
    """v6.0.5 Security & Enterprise Deployment Hardening.

    Security hardening changes application/deployment policy without taking ownership of
    a new business domain. The schema marker is advanced so readiness can fail closed
    when an older database is used with a hardened runtime.
    """
    ensure_v604_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.5', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.5', CURRENT_TIMESTAMP)"))


def ensure_v606_schema(engine: Engine) -> None:
    """v6.0.6 Controlled Automotive Pilot & User Acceptance.

    Adds pilot/UAT evidence tables through SQLAlchemy metadata.create_all and advances the
    operational marker. Pilot evidence measures workflow outcomes, not employee performance.
    """
    ensure_v605_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.6', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.6', CURRENT_TIMESTAMP)"))


def ensure_v607_schema(engine: Engine) -> None:
    """v6.0.7 UX Simplification & Pilot Feedback Closure.

    Adds aggregate pilot usability issue evidence through SQLAlchemy metadata.create_all and advances
    the operational marker. Role-focused UX remains a presentation layer and never widens ACL.
    """
    ensure_v606_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.7', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.7', CURRENT_TIMESTAMP)"))


def ensure_v608_schema(engine: Engine) -> None:
    """v6.0.8 Observability, Reliability & Production Support.

    Adds only operator/SLI evidence tables through SQLAlchemy metadata.create_all and advances
    the operational schema marker. No engineering-domain source of truth is changed.
    """
    ensure_v607_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.8', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.8', CURRENT_TIMESTAMP)"))


def ensure_v609_schema(engine: Engine) -> None:
    """v6.0.9 Production Operations Acceptance & Game Days.

    Adds only operations-acceptance evidence tables through SQLAlchemy metadata.create_all and
    advances the operational schema marker. Fault injection remains outside the application.
    """
    ensure_v608_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.9', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.0.9', CURRENT_TIMESTAMP)"))


def ensure_v610_schema(engine: Engine) -> None:
    """v6.1.0 Corporate Deployment & Pilot Launch Kit.

    Deployment planning is derived/configuration-only; no new business tables are added.
    The operational marker advances so mixed runtime/database releases fail closed.
    """
    ensure_v609_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.1.0', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.1.0', CURRENT_TIMESTAMP)"))


def ensure_v620_schema(engine: Engine) -> None:
    """v6.2.0 Architecture Simplification.

    No new business-domain tables are introduced. The release consolidates runtime contracts,
    bounded contexts and optional derived stores while keeping the legacy schema/API compatible.
    """
    ensure_v610_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.2.0', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.2.0', CURRENT_TIMESTAMP)"))


def ensure_v630_schema(engine: Engine) -> None:
    """v6.3.0 Manufacturing Work Instructions & Station Intelligence.

    New work-instruction, translation-memory and manufacturing-layout tables are created
    through SQLAlchemy metadata.create_all. Existing process stations gain additive operator
    context fields so shop-floor layouts can explain who does what without becoming MES control.
    """
    ensure_v620_schema(engine)
    _add_missing_columns(engine, "process_stations", {
        "operator_role": "VARCHAR(255)",
        "headcount": "INTEGER DEFAULT 1",
        "work_content": "TEXT",
        "takt_time_sec": "FLOAT",
    })
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.0', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.0', CURRENT_TIMESTAMP)"))


def ensure_v632_schema(engine: Engine) -> None:
    """v6.3.2 Transaction & Projection Reliability.

    Adds PostgreSQL-authoritative search chunks plus an outbox/receipt ledger for rebuildable
    Qdrant, Neo4j and MinIO projections. Tables are created by metadata.create_all before this
    marker is advanced; no authoritative engineering entity is moved out of PostgreSQL.
    """
    ensure_v630_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v632_outbox_dispatch ON projection_outbox_events (status, available_at, created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v632_outbox_target_status ON projection_outbox_events (target, status, created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v632_chunks_doc_index ON document_search_chunks (document_id, chunk_index)"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.2', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.2', CURRENT_TIMESTAMP)"))


def ensure_v633_schema(engine: Engine) -> None:
    """v6.3.3 Database & Domain Integrity Hardening.

    Adds optimistic-concurrency row versions to human-edited engineering records. Fresh
    databases also receive model-level CHECK constraints; legacy upgrades preserve data
    and add version columns additively/idempotently.
    """
    ensure_v632_schema(engine)
    for table in ("change_requests", "process_stations", "work_instructions", "manufacturing_layouts"):
        _add_missing_columns(engine, table, {"row_version": "INTEGER DEFAULT 1 NOT NULL"})
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        for table in ("change_requests", "process_stations", "work_instructions", "manufacturing_layouts"):
            if table in tables:
                conn.execute(text(f"UPDATE {table} SET row_version=1 WHERE row_version IS NULL OR row_version < 1"))
        invariant_queries = [
            ("bom_items", "quantity <= 0", "BOM quantity must be > 0"),
            ("process_stations", "headcount < 1 OR (takt_time_sec IS NOT NULL AND takt_time_sec < 0)", "Station headcount/takt invariant violated"),
            ("work_instructions", "cycle_time_sec IS NOT NULL AND cycle_time_sec < 0", "Work-instruction cycle time must be >= 0"),
        ]
        for table, predicate, message in invariant_queries:
            if table in tables and int(conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {predicate}")).scalar() or 0) > 0:
                raise RuntimeError(f"v6.3.3 migration blocked: {message}; repair invalid legacy rows before retry")
        if engine.dialect.name == "postgresql":
            checks = [
                ("bom_items", "ck_bom_quantity_positive", "quantity > 0"),
                ("process_stations", "ck_process_station_headcount_positive", "headcount >= 1"),
                ("process_stations", "ck_process_station_takt_nonnegative", "takt_time_sec IS NULL OR takt_time_sec >= 0"),
                ("work_instructions", "ck_work_instruction_cycle_nonnegative", "cycle_time_sec IS NULL OR cycle_time_sec >= 0"),
            ]
            for table, name, predicate in checks:
                if table not in tables:
                    continue
                conn.execute(text(f"""DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}') THEN
                        ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({predicate});
                    END IF;
                END $$;"""))
        elif engine.dialect.name == "sqlite":
            conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v633_bom_guard_i BEFORE INSERT ON bom_items WHEN NEW.quantity <= 0 BEGIN SELECT RAISE(ABORT, 'BOM quantity must be > 0'); END"))
            conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v633_bom_guard_u BEFORE UPDATE OF quantity ON bom_items WHEN NEW.quantity <= 0 BEGIN SELECT RAISE(ABORT, 'BOM quantity must be > 0'); END"))
            conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v633_station_guard_i BEFORE INSERT ON process_stations WHEN NEW.headcount < 1 OR (NEW.takt_time_sec IS NOT NULL AND NEW.takt_time_sec < 0) BEGIN SELECT RAISE(ABORT, 'Station invariant violated'); END"))
            conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v633_station_guard_u BEFORE UPDATE OF headcount, takt_time_sec ON process_stations WHEN NEW.headcount < 1 OR (NEW.takt_time_sec IS NOT NULL AND NEW.takt_time_sec < 0) BEGIN SELECT RAISE(ABORT, 'Station invariant violated'); END"))
            conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v633_wi_guard_i BEFORE INSERT ON work_instructions WHEN NEW.cycle_time_sec IS NOT NULL AND NEW.cycle_time_sec < 0 BEGIN SELECT RAISE(ABORT, 'Work instruction cycle time must be >= 0'); END"))
            conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v633_wi_guard_u BEFORE UPDATE OF cycle_time_sec ON work_instructions WHEN NEW.cycle_time_sec IS NOT NULL AND NEW.cycle_time_sec < 0 BEGIN SELECT RAISE(ABORT, 'Work instruction cycle time must be >= 0'); END"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v633_change_version ON change_requests (id, row_version)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v633_station_version ON process_stations (id, row_version)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v633_wi_version ON work_instructions (id, row_version)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v633_layout_version ON manufacturing_layouts (id, row_version)"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.3', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.3', CURRENT_TIMESTAMP)"))


def ensure_v634_schema(engine: Engine) -> None:
    """v6.3.4 Engineering Revision & Conflict Management.

    Adds revision snapshots, write-idempotency receipts and edit-conflict telemetry.
    Existing duplicate approvals are not guessed or auto-corrected: migration fails closed
    before installing the one-approval-per-stage uniqueness guard.
    """
    ensure_v633_schema(engine)
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "change_approvals" in tables:
            duplicate = conn.execute(text("""
                SELECT change_id, stage, COUNT(*) AS n
                FROM change_approvals
                GROUP BY change_id, stage
                HAVING COUNT(*) > 1
                LIMIT 1
            """)).first()
            if duplicate:
                raise RuntimeError("v6.3.4 migration blocked: duplicate approval stage rows exist; resolve controlled approval history before retry")
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_v634_change_approval_stage_once ON change_approvals (change_id, stage)"))
        if "engineering_revision_snapshots" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v634_snapshot_business ON engineering_revision_snapshots (project_code, business_code, business_revision)"))
        if "write_idempotency_records" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v634_idempotency_created ON write_idempotency_records (created_at)"))
        if "edit_conflict_events" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v634_conflict_created ON edit_conflict_events (created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v634_conflict_entity ON edit_conflict_events (entity_type, entity_id, created_at)"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.4', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.4', CURRENT_TIMESTAMP)"))


def ensure_v635_schema(engine: Engine) -> None:
    """v6.3.5 Engineering Approval & Release Governance.

    Adds configurable approval policies/cases/records and release-package tables.
    Migration is additive/idempotent. Approval evidence is tamper-evident engineering
    evidence, not a qualified electronic signature.
    """
    ensure_v634_schema(engine)
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "engineering_approval_policies" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v635_policy_scope ON engineering_approval_policies (entity_type, project_code, manufacturing_area, active)"))
        if "engineering_approval_cases" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v635_case_entity ON engineering_approval_cases (entity_type, entity_id, status)"))
        if "engineering_approval_records" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v635_approval_record_case_order ON engineering_approval_records (case_id, stage_order)"))
        if "engineering_release_packages" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v635_release_scope ON engineering_release_packages (project_code, manufacturing_area, status)"))
        if "engineering_release_package_items" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v635_release_item_entity ON engineering_release_package_items (entity_type, entity_id)"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.5', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.5', CURRENT_TIMESTAMP)"))


def ensure_v636_schema(engine: Engine) -> None:
    """v6.3.6 Enterprise Identity & Policy Enforcement.

    Adds scoped identity policies/delegations and binds approval/release evidence to a
    sanitized corporate identity snapshot. Optional PostgreSQL RLS is deliberately scoped
    to the new identity-governance tables; existing engineering ACLs remain unchanged.
    """
    ensure_v635_schema(engine)
    _add_missing_columns(engine, "engineering_approval_cases", {"submitted_identity_json": "JSON"})
    _add_missing_columns(engine, "engineering_approval_records", {
        "identity_snapshot_json": "JSON", "assurance_json": "JSON",
    })
    _add_missing_columns(engine, "engineering_release_packages", {"released_identity_json": "JSON"})
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "engineering_identity_policies" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v636_identity_policy_scope ON engineering_identity_policies (action, project_code, manufacturing_area, entity_type, active)"))
        if "engineering_identity_delegations" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v636_delegation_delegate_validity ON engineering_identity_delegations (delegate, revoked_at, valid_from, valid_until)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v636_delegation_scope ON engineering_identity_delegations (project_code, manufacturing_area, entity_type)"))
        if engine.dialect.name == "postgresql":
            from app.core.config import get_settings
            if get_settings().governance_postgres_rls_enabled:
                if "engineering_identity_policies" in tables:
                    conn.execute(text("ALTER TABLE engineering_identity_policies ENABLE ROW LEVEL SECURITY"))
                    conn.execute(text("DROP POLICY IF EXISTS mgc_identity_policy_admin ON engineering_identity_policies"))
                    conn.execute(text("CREATE POLICY mgc_identity_policy_admin ON engineering_identity_policies USING (current_setting('mgc.is_admin', true) = 'true') WITH CHECK (current_setting('mgc.is_admin', true) = 'true')"))
                if "engineering_identity_delegations" in tables:
                    conn.execute(text("ALTER TABLE engineering_identity_delegations ENABLE ROW LEVEL SECURITY"))
                    conn.execute(text("DROP POLICY IF EXISTS mgc_identity_delegation_visibility ON engineering_identity_delegations"))
                    conn.execute(text("CREATE POLICY mgc_identity_delegation_visibility ON engineering_identity_delegations USING (current_setting('mgc.is_admin', true) = 'true' OR delegator = current_setting('mgc.user', true) OR delegate = current_setting('mgc.user', true)) WITH CHECK (current_setting('mgc.is_admin', true) = 'true')"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.6', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.6', CURRENT_TIMESTAMP)"))


def ensure_v637_schema(engine: Engine) -> None:
    """v6.3.7 Engineering Release Handover & Integration Safety.

    Adds immutable outbound handover jobs, target allowlisting and delivery receipts.
    External writes remain disabled by default and are never enabled by migration.
    """
    ensure_v636_schema(engine)
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "engineering_handover_targets" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v637_handover_target_system ON engineering_handover_targets (external_system_id, enabled, allow_write)"))
        if "engineering_handover_jobs" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v637_handover_job_status ON engineering_handover_jobs (status, created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v637_handover_job_package ON engineering_handover_jobs (package_id, target_id, created_at)"))
            # Immutable command identity: lifecycle/result fields may change, outbound command identity may not.
            if engine.dialect.name == "postgresql":
                conn.execute(text("""CREATE OR REPLACE FUNCTION mgc_v637_handover_immutable() RETURNS trigger AS $$
                BEGIN
                  IF NEW.package_id IS DISTINCT FROM OLD.package_id OR NEW.target_id IS DISTINCT FROM OLD.target_id
                     OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key OR NEW.mode IS DISTINCT FROM OLD.mode
                     OR NEW.manifest_sha256 IS DISTINCT FROM OLD.manifest_sha256 OR NEW.request_sha256 IS DISTINCT FROM OLD.request_sha256
                     OR NEW.manifest_json IS DISTINCT FROM OLD.manifest_json OR NEW.payload_json IS DISTINCT FROM OLD.payload_json
                     OR NEW.created_by IS DISTINCT FROM OLD.created_by OR NEW.maker_identity_json IS DISTINCT FROM OLD.maker_identity_json THEN
                    RAISE EXCEPTION 'v6.3.7 handover command fields are immutable';
                  END IF;
                  RETURN NEW;
                END; $$ LANGUAGE plpgsql"""))
                conn.execute(text("DROP TRIGGER IF EXISTS trg_v637_handover_immutable ON engineering_handover_jobs"))
                conn.execute(text("CREATE TRIGGER trg_v637_handover_immutable BEFORE UPDATE ON engineering_handover_jobs FOR EACH ROW EXECUTE FUNCTION mgc_v637_handover_immutable()"))
            elif engine.dialect.name == "sqlite":
                conn.execute(text("""CREATE TRIGGER IF NOT EXISTS trg_v637_handover_immutable BEFORE UPDATE ON engineering_handover_jobs
                WHEN NEW.package_id != OLD.package_id OR NEW.target_id != OLD.target_id OR NEW.idempotency_key != OLD.idempotency_key
                  OR NEW.mode != OLD.mode OR NEW.manifest_sha256 != OLD.manifest_sha256 OR NEW.request_sha256 != OLD.request_sha256
                  OR NEW.manifest_json != OLD.manifest_json OR NEW.payload_json != OLD.payload_json
                  OR NEW.created_by != OLD.created_by OR NEW.maker_identity_json != OLD.maker_identity_json
                BEGIN SELECT RAISE(ABORT, 'v6.3.7 handover command fields are immutable'); END"""))
        if "engineering_handover_receipts" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v637_handover_receipt_external ON engineering_handover_receipts (external_receipt_id, status)"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.7', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.7', CURRENT_TIMESTAMP)"))


def ensure_v638_schema(engine: Engine) -> None:
    """v6.3.8 Data Lifecycle, Retention & Compliance Hardening.

    Adds retention policies, legal holds, lifecycle state, maker-checker purge requests and
    append-only lifecycle evidence. Authoritative purge remains disabled by configuration;
    migration never deletes engineering data or projections.
    """
    ensure_v637_schema(engine)
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "engineering_retention_policies" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v638_retention_scope ON engineering_retention_policies (entity_type, project_code, manufacturing_area, active)"))
        if "engineering_legal_holds" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v638_hold_scope ON engineering_legal_holds (active, project_code, manufacturing_area, entity_type, entity_id)"))
        if "engineering_purge_requests" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v638_purge_status ON engineering_purge_requests (status, created_at)"))
        if "engineering_lifecycle_events" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v638_lifecycle_entity ON engineering_lifecycle_events (entity_type, entity_id, created_at)"))
            # Append-only lifecycle evidence: history cannot be rewritten or removed through normal SQL.
            if engine.dialect.name == "postgresql":
                conn.execute(text("""CREATE OR REPLACE FUNCTION mgc_v638_lifecycle_append_only() RETURNS trigger AS $$
                BEGIN RAISE EXCEPTION 'v6.3.8 lifecycle events are append-only'; END; $$ LANGUAGE plpgsql"""))
                conn.execute(text("DROP TRIGGER IF EXISTS trg_v638_lifecycle_update ON engineering_lifecycle_events"))
                conn.execute(text("DROP TRIGGER IF EXISTS trg_v638_lifecycle_delete ON engineering_lifecycle_events"))
                conn.execute(text("CREATE TRIGGER trg_v638_lifecycle_update BEFORE UPDATE ON engineering_lifecycle_events FOR EACH ROW EXECUTE FUNCTION mgc_v638_lifecycle_append_only()"))
                conn.execute(text("CREATE TRIGGER trg_v638_lifecycle_delete BEFORE DELETE ON engineering_lifecycle_events FOR EACH ROW EXECUTE FUNCTION mgc_v638_lifecycle_append_only()"))
            elif engine.dialect.name == "sqlite":
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v638_lifecycle_update BEFORE UPDATE ON engineering_lifecycle_events BEGIN SELECT RAISE(ABORT, 'v6.3.8 lifecycle events are append-only'); END"))
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v638_lifecycle_delete BEFORE DELETE ON engineering_lifecycle_events BEGIN SELECT RAISE(ABORT, 'v6.3.8 lifecycle events are append-only'); END"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.8', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.8', CURRENT_TIMESTAMP)"))


def ensure_v639_schema(engine: Engine) -> None:
    """v6.3.9 Database Performance & Scale Hardening.

    Adds only additive/composite indexes and schema marker. No engineering records are rewritten.
    Indexes target the dominant project/area/revision/keyset access paths used by Object 360,
    BOM, Work Instructions, operational queues and audit browsing.
    """
    ensure_v638_schema(engine)
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        statements = {
            "documents": [
                "CREATE INDEX IF NOT EXISTS idx_v639_documents_project_area_created ON documents (project_code, manufacturing_area, created_at, id)",
                "CREATE INDEX IF NOT EXISTS idx_v639_documents_part_revision ON documents (part_number, revision, doc_type)",
            ],
            "bom_items": [
                "CREATE INDEX IF NOT EXISTS idx_v639_bom_parent_rev_child ON bom_items (parent_part_number, parent_revision, child_part_number)",
                "CREATE INDEX IF NOT EXISTS idx_v639_bom_source_parent ON bom_items (source_document_id, parent_part_number)",
            ],
            "work_instructions": [
                "CREATE INDEX IF NOT EXISTS idx_v639_wi_scope_station_status ON work_instructions (project_code, manufacturing_area, station_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_v639_wi_code_revision ON work_instructions (project_code, code, revision)",
            ],
            "manufacturing_lines": [
                "CREATE INDEX IF NOT EXISTS idx_v639_lines_scope_status ON manufacturing_lines (project_code, manufacturing_area, status)",
            ],
            "process_stations": [
                "CREATE INDEX IF NOT EXISTS idx_v639_stations_line_sequence ON process_stations (line_id, sequence, id)",
            ],
            "process_operations": [
                "CREATE INDEX IF NOT EXISTS idx_v639_operations_station_sequence ON process_operations (station_id, sequence, id)",
            ],
            "change_requests": [
                "CREATE INDEX IF NOT EXISTS idx_v639_changes_status_priority_updated ON change_requests (status, priority, updated_at, id)",
                "CREATE INDEX IF NOT EXISTS idx_v639_changes_part_status ON change_requests (part_number, status)",
            ],
            "engineering_workflow_cases": [
                "CREATE INDEX IF NOT EXISTS idx_v639_workflow_scope_status_due ON engineering_workflow_cases (project_code, manufacturing_area, status, due_at)",
            ],
            "projection_outbox_events": [
                "CREATE INDEX IF NOT EXISTS idx_v639_projection_claim ON projection_outbox_events (status, available_at, locked_at, created_at)",
            ],
            "engineering_handover_jobs": [
                "CREATE INDEX IF NOT EXISTS idx_v639_handover_status_updated ON engineering_handover_jobs (status, updated_at, id)",
            ],
            "engineering_purge_requests": [
                "CREATE INDEX IF NOT EXISTS idx_v639_purge_status_updated ON engineering_purge_requests (status, updated_at, id)",
            ],
            "audit_events": [
                "CREATE INDEX IF NOT EXISTS idx_v639_audit_keyset ON audit_events (created_at, id)",
                "CREATE INDEX IF NOT EXISTS idx_v639_audit_entity_created ON audit_events (entity_type, entity_id, created_at)",
            ],
            "document_search_chunks": [
                "CREATE INDEX IF NOT EXISTS idx_v639_search_chunks_document_order ON document_search_chunks (document_id, chunk_index, id)",
            ],
        }
        for table, ddls in statements.items():
            if table in tables:
                for ddl in ddls:
                    conn.execute(text(ddl))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.9', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.9', CURRENT_TIMESTAMP)"))


def ensure_v6310_schema(engine: Engine) -> None:
    """v6.3.10 Cache, Read Models & Object 360 Performance.

    Adds only rebuildable read-model storage and indexes. Read models/cache are explicitly
    non-authoritative and may be deleted/rebuilt without engineering data loss.
    """
    ensure_v639_schema(engine)
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "engineering_read_models" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6310_read_model_scope ON engineering_read_models (model_type, project_code, manufacturing_area, status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6310_read_model_stale ON engineering_read_models (status, invalidated_at, updated_at)"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.10', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.10', CURRENT_TIMESTAMP)"))


def ensure_v6311_schema(engine: Engine) -> None:
    """v6.3.11 Background Jobs, Scheduler & Workload Isolation.

    Extends the existing ComputeJob ledger with project/resource/priority/progress/cancellation,
    bounded retry/DLQ and worker timing fields. The migration is additive and does not move
    authoritative engineering data into Redis/Celery.
    """
    ensure_v6310_schema(engine)
    ts = "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME"
    _add_missing_columns(engine, "compute_jobs", {
        "project_code": "VARCHAR(64)",
        "manufacturing_area": "VARCHAR(64)",
        "resource_class": "VARCHAR(32) DEFAULT 'cpu'",
        "priority": "INTEGER DEFAULT 4",
        "progress_percent": "INTEGER DEFAULT 0",
        "progress_message": "VARCHAR(512)",
        "cancellation_requested": "BOOLEAN DEFAULT FALSE" if engine.dialect.name == "postgresql" else "BOOLEAN DEFAULT 0",
        "attempt_count": "INTEGER DEFAULT 0",
        "max_attempts": "INTEGER DEFAULT 3",
        "timeout_seconds": "INTEGER DEFAULT 1800",
        "worker_id": "VARCHAR(255)",
        "started_at": ts,
        "heartbeat_at": ts,
        "finished_at": ts,
        "dead_lettered_at": ts,
    })
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "compute_jobs" in tables:
            conn.execute(text("UPDATE compute_jobs SET resource_class='cpu' WHERE resource_class IS NULL OR resource_class=''"))
            conn.execute(text("UPDATE compute_jobs SET queue='cpu' WHERE queue IS NULL OR queue='' OR queue='heavy'"))
            conn.execute(text("UPDATE compute_jobs SET priority=4 WHERE priority IS NULL OR priority < 0 OR priority > 9"))
            conn.execute(text("UPDATE compute_jobs SET progress_percent=0 WHERE progress_percent IS NULL OR progress_percent < 0 OR progress_percent > 100"))
            conn.execute(text("UPDATE compute_jobs SET attempt_count=0 WHERE attempt_count IS NULL OR attempt_count < 0"))
            conn.execute(text("UPDATE compute_jobs SET max_attempts=3 WHERE max_attempts IS NULL OR max_attempts < 1"))
            conn.execute(text("UPDATE compute_jobs SET timeout_seconds=1800 WHERE timeout_seconds IS NULL OR timeout_seconds < 1"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6311_jobs_project_resource_status ON compute_jobs (project_code, resource_class, status, created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6311_jobs_queue_priority ON compute_jobs (queue, status, priority, created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6311_jobs_dlq ON compute_jobs (status, dead_lettered_at, created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6311_jobs_heartbeat ON compute_jobs (status, heartbeat_at, updated_at)"))
            if engine.dialect.name == "postgresql":
                conn.execute(text("""DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_v6311_job_priority') THEN
                        ALTER TABLE compute_jobs ADD CONSTRAINT ck_v6311_job_priority CHECK (priority BETWEEN 0 AND 9);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_v6311_job_progress') THEN
                        ALTER TABLE compute_jobs ADD CONSTRAINT ck_v6311_job_progress CHECK (progress_percent BETWEEN 0 AND 100);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_v6311_job_attempts') THEN
                        ALTER TABLE compute_jobs ADD CONSTRAINT ck_v6311_job_attempts CHECK (attempt_count >= 0 AND max_attempts >= 1);
                    END IF;
                END $$;"""))
            elif engine.dialect.name == "sqlite":
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v6311_job_priority_i BEFORE INSERT ON compute_jobs WHEN NEW.priority < 0 OR NEW.priority > 9 BEGIN SELECT RAISE(ABORT, 'Compute job priority out of range'); END"))
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v6311_job_priority_u BEFORE UPDATE OF priority ON compute_jobs WHEN NEW.priority < 0 OR NEW.priority > 9 BEGIN SELECT RAISE(ABORT, 'Compute job priority out of range'); END"))
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v6311_job_progress_i BEFORE INSERT ON compute_jobs WHEN NEW.progress_percent < 0 OR NEW.progress_percent > 100 BEGIN SELECT RAISE(ABORT, 'Compute job progress out of range'); END"))
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v6311_job_progress_u BEFORE UPDATE OF progress_percent ON compute_jobs WHEN NEW.progress_percent < 0 OR NEW.progress_percent > 100 BEGIN SELECT RAISE(ABORT, 'Compute job progress out of range'); END"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.11', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.11', CURRENT_TIMESTAMP)"))


def ensure_v6313_schema(engine: Engine) -> None:
    """v6.3.13 Execution Recovery & Job Lease Safety.

    Adds delivery fencing/generation, worker lease expiry and auditable recovery metadata to
    ComputeJob. PostgreSQL remains the authoritative job ledger; Redis/Celery stays transport.
    """
    ensure_v6311_schema(engine)
    ts = "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "DATETIME"
    _add_missing_columns(engine, "compute_jobs", {
        "dispatch_token": "VARCHAR(36)",
        "dispatch_generation": "INTEGER DEFAULT 0",
        "last_dispatch_at": ts,
        "lease_expires_at": ts,
        "recovery_count": "INTEGER DEFAULT 0",
        "last_recovery_at": ts,
        "recovery_reason": "VARCHAR(512)",
    })
    # Keep the migration independently replayable: bootstrap normally calls metadata.create_all()
    # first, but an explicit migration rehearsal must also be able to create the recovery ledger.
    with engine.begin() as conn:
        if "compute_jobs" in set(inspect(engine).get_table_names()):
            conn.execute(text(f"""CREATE TABLE IF NOT EXISTS compute_job_recovery_events (
                id VARCHAR(36) PRIMARY KEY,
                job_id VARCHAR(36) NOT NULL REFERENCES compute_jobs(id),
                recovery_number INTEGER NOT NULL DEFAULT 1,
                action VARCHAR(64) NOT NULL,
                reason VARCHAR(512) NOT NULL,
                actor VARCHAR(255) NOT NULL DEFAULT 'scheduler',
                prior_status VARCHAR(32),
                prior_worker_id VARCHAR(255),
                prior_celery_task_id VARCHAR(64),
                prior_dispatch_generation INTEGER NOT NULL DEFAULT 0,
                new_dispatch_generation INTEGER,
                created_at {ts} DEFAULT CURRENT_TIMESTAMP
            )"""))
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        if "compute_jobs" in tables:
            conn.execute(text("UPDATE compute_jobs SET dispatch_generation=0 WHERE dispatch_generation IS NULL OR dispatch_generation < 0"))
            conn.execute(text("UPDATE compute_jobs SET recovery_count=0 WHERE recovery_count IS NULL OR recovery_count < 0"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6313_jobs_dispatch_token ON compute_jobs (dispatch_token)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6313_jobs_dispatch_time ON compute_jobs (status, last_dispatch_at, created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6313_jobs_lease ON compute_jobs (status, lease_expires_at, heartbeat_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6313_jobs_recovery ON compute_jobs (status, recovery_count, last_recovery_at)"))
            if engine.dialect.name == "postgresql":
                conn.execute(text("""DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_v6313_job_recovery_counters') THEN
                        ALTER TABLE compute_jobs ADD CONSTRAINT ck_v6313_job_recovery_counters
                        CHECK (dispatch_generation >= 0 AND recovery_count >= 0);
                    END IF;
                END $$;"""))
            elif engine.dialect.name == "sqlite":
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v6313_job_counters_i BEFORE INSERT ON compute_jobs WHEN NEW.dispatch_generation < 0 OR NEW.recovery_count < 0 BEGIN SELECT RAISE(ABORT, 'Compute job recovery counters out of range'); END"))
                conn.execute(text("CREATE TRIGGER IF NOT EXISTS trg_v6313_job_counters_u BEFORE UPDATE OF dispatch_generation, recovery_count ON compute_jobs WHEN NEW.dispatch_generation < 0 OR NEW.recovery_count < 0 BEGIN SELECT RAISE(ABORT, 'Compute job recovery counters out of range'); END"))
        if "compute_job_recovery_events" in tables:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6313_recovery_job_time ON compute_job_recovery_events (job_id, created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_v6313_recovery_action_time ON compute_job_recovery_events (action, created_at)"))
        conn.execute(text("DELETE FROM mgc_schema_state WHERE id=1"))
        if engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.13', NOW())"))
        else:
            conn.execute(text("INSERT INTO mgc_schema_state (id, schema_version, applied_at) VALUES (1, '6.3.13', CURRENT_TIMESTAMP)"))
