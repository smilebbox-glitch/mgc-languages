from __future__ import annotations

import enum
import hashlib
import json
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db.models import (
    ChangeEvent,
    ChangeEventState,
    ChangeRequest,
    Document,
    DocumentActivity,
    DocumentActivityState,
    Relationship,
)
from app.db.session import Base
from app.services.audit import _activity_digest
from app.services.engineering_change import _event_digest

SNAPSHOT_SCHEMA = "mgc.authoritative-consistency.v1"
# .mgc-backup contains temporary Qdrant transfer material and is intentionally excluded
# by backup_core.sh from authoritative evidence storage archives.
EXCLUDED_STORAGE_PREFIXES = {".mgc-backup", ".mgc-ha"}
DOCUMENT_REFERENCE_COLUMNS = {
    "document_id",
    "source_document_id",
    "evidence_document_id",
    "linked_document_id",
}
DOCUMENT_REFERENCE_LIST_COLUMNS = {
    "document_ids",
    "evidence_document_ids",
    "affected_document_ids",
    "source_document_ids",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bytes):
        return {"bytes_sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def _canonical(value: Any) -> bytes:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _under_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_evidence_path(raw: str | None, root: Path) -> tuple[Path | None, str | None]:
    if not raw:
        return None, "empty_path"
    source = Path(raw)
    candidates: list[Path] = []
    try:
        candidates.append(source.expanduser().resolve())
    except OSError:
        pass
    if not source.is_absolute():
        try:
            candidates.append((root / source).resolve())
        except OSError:
            pass
    for candidate in candidates:
        if _under_root(candidate, root):
            return candidate, None
    return (candidates[0] if candidates else source), "outside_storage_root"


def _finding(code: str, severity: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "details": _jsonable(details)}


def _database_fingerprint(db: Session) -> dict[str, Any]:
    """Hash logical row content in deterministic table/PK order.

    The fingerprint is intentionally database-engine independent so a restore can be
    compared even when PostgreSQL dump bytes are not deterministic. It is a maintenance
    operation and may be I/O intensive on large data sets.
    """
    global_hash = hashlib.sha256()
    tables: list[dict[str, Any]] = []
    conn = db.connection()

    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        pk = list(table.primary_key.columns)
        order = pk if pk else list(table.columns)
        stmt = select(table)
        if order:
            stmt = stmt.order_by(*order)
        row_hash = hashlib.sha256()
        count = 0
        result = conn.execution_options(stream_results=True).execute(stmt).mappings()
        for row in result:
            encoded = _canonical(dict(row))
            row_hash.update(encoded)
            row_hash.update(b"\n")
            count += 1
        digest = row_hash.hexdigest()
        tables.append({"table": table.name, "rows": count, "sha256": digest})
        global_hash.update(f"{table.name}\0{count}\0{digest}\n".encode("utf-8"))

    # mgc_schema_state is migration-managed rather than ORM-managed; bind it explicitly.
    schema_marker = None
    try:
        schema_marker = conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one_or_none()
    except Exception:
        schema_marker = None
    global_hash.update(f"mgc_schema_state\0{schema_marker or ''}\n".encode("utf-8"))

    sequence_rows: list[dict[str, Any]] = []
    pitr: dict[str, Any] = {"engine": conn.dialect.name, "supported": conn.dialect.name == "postgresql"}
    if conn.dialect.name == "postgresql":
        try:
            seq_result = conn.execute(text("SELECT schemaname, sequencename, last_value, start_value, increment_by FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename")).mappings()
            for row in seq_result:
                item = _jsonable(dict(row)); sequence_rows.append(item)
                global_hash.update(b"sequence\0"); global_hash.update(_canonical(item)); global_hash.update(b"\n")
        except Exception as exc:
            pitr["sequence_probe_error"] = type(exc).__name__
        try:
            pitr.update({
                "wal_level": conn.execute(text("SHOW wal_level")).scalar_one(),
                "archive_mode": conn.execute(text("SHOW archive_mode")).scalar_one(),
                "archive_timeout": conn.execute(text("SHOW archive_timeout")).scalar_one(),
                "checkpoint_lsn": conn.execute(text("SELECT pg_current_wal_lsn()::text")).scalar_one(),
                "in_recovery": bool(conn.execute(text("SELECT pg_is_in_recovery()")).scalar_one()),
            })
            cmd = str(conn.execute(text("SHOW archive_command")).scalar_one() or "")
            pitr["archive_command_configured"] = bool(cmd.strip()) and cmd.strip() not in {"(disabled)", ""}
            pitr["pitr_ready"] = pitr.get("wal_level") in {"replica", "logical"} and pitr.get("archive_mode") in {"on", "always"} and pitr["archive_command_configured"]
        except Exception as exc:
            pitr["probe_error"] = type(exc).__name__
            pitr["pitr_ready"] = False
    return {"logical_sha256": global_hash.hexdigest(), "schema_marker": schema_marker, "tables": tables, "sequences": sequence_rows, "pitr": pitr}


def _storage_fingerprint(root: Path, *, hash_files: bool) -> tuple[dict[str, Any], list[dict[str, Any]], dict[Path, str]]:
    findings: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    files = 0
    bytes_total = 0
    symlinks = 0
    hash_cache: dict[Path, str] = {}

    if not root.exists() or not root.is_dir():
        findings.append(_finding("storage_root_missing", "critical", "Evidence storage root is missing or not a directory", path=str(root)))
        return {"tree_sha256": None, "files": 0, "bytes": 0, "hash_mode": "full" if hash_files else "metadata"}, findings, hash_cache

    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in EXCLUDED_STORAGE_PREFIXES:
            continue
        if path.is_symlink():
            symlinks += 1
            target = os.readlink(path)
            findings.append(_finding("storage_symlink", "critical", "Authoritative evidence storage contains a symlink", path=rel.as_posix(), target=target))
            digest.update(f"L\0{rel.as_posix()}\0{target}\n".encode("utf-8"))
            continue
        if not path.is_file():
            continue
        stat = path.stat()
        files += 1
        bytes_total += stat.st_size
        content_hash = _sha256_file(path) if hash_files else None
        if content_hash is not None:
            hash_cache[path.resolve()] = content_hash
        line = {"path": rel.as_posix(), "size": stat.st_size, "sha256": content_hash}
        digest.update(_canonical(line)); digest.update(b"\n")

    return {
        "tree_sha256": digest.hexdigest(),
        "files": files,
        "bytes": bytes_total,
        "symlinks": symlinks,
        "hash_mode": "full" if hash_files else "metadata",
    }, findings, hash_cache


def _document_integrity(db: Session, root: Path, *, hash_files: bool, max_findings: int, hash_cache: dict[Path, str] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    findings: list[dict[str, Any]] = []
    docs = db.scalars(select(Document).order_by(Document.id)).all()
    doc_ids = {d.id for d in docs}
    checked = 0
    hashed = 0
    preview_missing = 0

    for doc in docs:
        checked += 1
        path, error = _resolve_evidence_path(doc.stored_path, root)
        if error:
            findings.append(_finding("document_path_outside_storage", "critical", "Document evidence path escapes the authoritative storage root", document_id=doc.id, stored_path=doc.stored_path))
            if len(findings) >= max_findings:
                continue
        elif path is None or not path.exists() or not path.is_file():
            findings.append(_finding("document_file_missing", "critical", "Document record points to missing evidence", document_id=doc.id, stored_path=doc.stored_path))
        else:
            stat = path.stat()
            if int(doc.size_bytes or 0) != int(stat.st_size):
                findings.append(_finding("document_size_mismatch", "critical", "Document evidence size differs from PostgreSQL metadata", document_id=doc.id, expected=doc.size_bytes, actual=stat.st_size))
            if not isinstance(doc.sha256, str) or len(doc.sha256) != 64:
                findings.append(_finding("document_sha256_missing", "critical", "Document record has no valid SHA-256 anchor", document_id=doc.id))
            elif hash_files:
                actual = (hash_cache or {}).get(path.resolve()) or _sha256_file(path)
                hashed += 1
                if actual.lower() != doc.sha256.lower():
                    findings.append(_finding("document_sha256_mismatch", "critical", "Document evidence content does not match PostgreSQL SHA-256", document_id=doc.id, expected=doc.sha256, actual=actual))
        if doc.preview_path:
            preview, preview_error = _resolve_evidence_path(doc.preview_path, root)
            if preview_error:
                findings.append(_finding("preview_path_outside_storage", "warning", "Derived preview path escapes evidence storage", document_id=doc.id, preview_path=doc.preview_path))
            elif preview is None or not preview.exists():
                preview_missing += 1
                findings.append(_finding("preview_missing", "warning", "Derived preview is missing and should be rebuilt", document_id=doc.id, preview_path=doc.preview_path))
        if len(findings) > max_findings:
            findings = findings[:max_findings]

    return {"records": len(docs), "files_checked": checked, "files_hashed": hashed, "missing_previews": preview_missing}, findings, doc_ids


def _document_reference_integrity(db: Session, doc_ids: set[str], *, max_findings: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate scalar/list document references that are not uniformly protected by FKs."""
    findings: list[dict[str, Any]] = []
    references = 0
    dangling = 0
    conn = db.connection()

    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        ref_columns = [c for c in table.columns if c.name in DOCUMENT_REFERENCE_COLUMNS or c.name in DOCUMENT_REFERENCE_LIST_COLUMNS]
        if not ref_columns:
            continue
        pk_cols = list(table.primary_key.columns)
        select_cols = pk_cols + [c for c in ref_columns if c not in pk_cols]
        stmt = select(*select_cols)
        if pk_cols:
            stmt = stmt.order_by(*pk_cols)
        for row in conn.execute(stmt).mappings():
            row_id = "/".join(str(row[c.name]) for c in pk_cols) if pk_cols else "unknown"
            for col in ref_columns:
                value = row[col.name]
                if value is None or value == "":
                    continue
                values: Iterable[Any]
                if col.name in DOCUMENT_REFERENCE_LIST_COLUMNS:
                    if not isinstance(value, list):
                        findings.append(_finding("invalid_document_reference_list", "critical", "Document reference list is not a JSON list", table=table.name, row_id=row_id, column=col.name))
                        dangling += 1
                        continue
                    values = value
                else:
                    values = [value]
                for ref in values:
                    if not isinstance(ref, str) or not ref:
                        continue
                    references += 1
                    if ref not in doc_ids:
                        dangling += 1
                        if len(findings) < max_findings:
                            findings.append(_finding("dangling_document_reference", "critical", "Engineering record references a non-existent document", table=table.name, row_id=row_id, column=col.name, document_id=ref))
    return {"references_checked": references, "dangling": dangling}, findings


def _tamper_chain_integrity(db: Session, *, max_findings: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    doc_events = db.scalars(select(DocumentActivity).order_by(DocumentActivity.document_id, DocumentActivity.created_at, DocumentActivity.id)).all()
    doc_states = {x.document_id: x for x in db.scalars(select(DocumentActivityState)).all()}
    by_doc: dict[str, list[DocumentActivity]] = {}
    for row in doc_events:
        by_doc.setdefault(row.document_id, []).append(row)
    invalid_doc_chains = 0
    for document_id, rows in by_doc.items():
        previous = ""; valid = True
        for row in rows:
            expected = _activity_digest(row.document_id, row.user, row.action, row.summary, row.details or {}, row.created_at, previous)
            if row.previous_hash != previous or row.event_hash != expected:
                valid = False
            previous = row.event_hash
        state = doc_states.get(document_id)
        if state is None or state.head_hash != previous or int(state.event_count or 0) != len(rows):
            valid = False
        if not valid:
            invalid_doc_chains += 1
            if len(findings) < max_findings:
                findings.append(_finding("document_activity_chain_invalid", "critical", "Tamper-evident document activity chain is invalid", document_id=document_id, events=len(rows)))
    for document_id, state in doc_states.items():
        if document_id not in by_doc and (state.head_hash or int(state.event_count or 0)):
            invalid_doc_chains += 1
            if len(findings) < max_findings:
                findings.append(_finding("document_activity_tail_missing", "critical", "Document activity state has no matching event rows", document_id=document_id))

    changes = set(db.scalars(select(ChangeRequest.id)).all())
    change_events = db.scalars(select(ChangeEvent).order_by(ChangeEvent.change_id, ChangeEvent.created_at, ChangeEvent.id)).all()
    change_states = {x.change_id: x for x in db.scalars(select(ChangeEventState)).all()}
    by_change: dict[str, list[ChangeEvent]] = {}
    for row in change_events:
        by_change.setdefault(row.change_id, []).append(row)
    invalid_change_chains = 0
    for change_id, rows in by_change.items():
        previous = ""; valid = True
        for row in rows:
            expected = _event_digest(row.change_id, row.user, row.action, row.summary, row.details or {}, row.created_at, previous)
            if row.previous_hash != previous or row.event_hash != expected:
                valid = False
            previous = row.event_hash
        state = change_states.get(change_id)
        if state is None or state.head_hash != previous or int(state.event_count or 0) != len(rows) or change_id not in changes:
            valid = False
        if not valid:
            invalid_change_chains += 1
            if len(findings) < max_findings:
                findings.append(_finding("change_event_chain_invalid", "critical", "Tamper-evident engineering change chain is invalid", change_id=change_id, events=len(rows)))
    for change_id, state in change_states.items():
        if change_id not in by_change and (state.head_hash or int(state.event_count or 0)):
            invalid_change_chains += 1
            if len(findings) < max_findings:
                findings.append(_finding("change_event_tail_missing", "critical", "Engineering change state has no matching event rows", change_id=change_id))

    return {
        "document_activity_events": len(doc_events),
        "invalid_document_chains": invalid_doc_chains,
        "change_events": len(change_events),
        "invalid_change_chains": invalid_change_chains,
    }, findings


def build_consistency_snapshot(
    db: Session,
    *,
    storage_root: Path | str | None = None,
    hash_files: bool = True,
    hash_database: bool = True,
    max_findings: int = 200,
    epoch_id: str | None = None,
) -> dict[str, Any]:
    root = Path(storage_root or get_settings().storage_dir).expanduser().resolve()
    max_findings = max(10, min(int(max_findings), 2000))
    findings: list[dict[str, Any]] = []

    # Hash the evidence tree once and reuse those content hashes for per-document anchors.
    # Large CAD/evidence files are therefore not read twice during the same maintenance scan.
    storage_report, storage_findings, storage_hashes = _storage_fingerprint(root, hash_files=hash_files)
    findings.extend(storage_findings)
    document_report, document_findings, doc_ids = _document_integrity(db, root, hash_files=hash_files, max_findings=max_findings, hash_cache=storage_hashes)
    findings.extend(document_findings)
    reference_report, reference_findings = _document_reference_integrity(db, doc_ids, max_findings=max_findings)
    findings.extend(reference_findings)
    chain_report, chain_findings = _tamper_chain_integrity(db, max_findings=max_findings)
    findings.extend(chain_findings)

    if hash_database:
        database_report = _database_fingerprint(db)
    else:
        try:
            marker = db.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one_or_none()
        except Exception:
            marker = None
        database_report = {"logical_sha256": None, "schema_marker": marker, "tables": []}

    if database_report.get("schema_marker") != SCHEMA_VERSION:
        findings.append(_finding("schema_marker_mismatch", "critical", "Database schema marker differs from runtime contract", expected=SCHEMA_VERSION, actual=database_report.get("schema_marker")))

    critical = sum(1 for x in findings if x["severity"] == "critical")
    warnings = sum(1 for x in findings if x["severity"] == "warning")
    status = "pass" if critical == 0 else "fail"
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "epoch_id": epoch_id or str(uuid.uuid4()),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "critical_findings": critical,
        "warning_findings": warnings,
        "storage_root": str(root),
        "database": database_report,
        "storage": storage_report,
        "documents": document_report,
        "document_references": reference_report,
        "tamper_evident_chains": chain_report,
        "findings": findings[:max_findings],
        "truncated_findings": max(0, len(findings) - max_findings),
        "policy": {
            "authoritative": ["postgresql", "evidence_storage"],
            "derived_rebuildable": ["qdrant", "neo4j", "engineering_read_models"],
            "file_hashing": bool(hash_files),
            "database_row_hashing": bool(hash_database),
            "backup_eligible": status == "pass" and bool(hash_files) and bool(hash_database),
        },
    }
    return snapshot


def compare_consistency_snapshots(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "snapshot_schema": expected.get("schema") == actual.get("schema") == SNAPSHOT_SCHEMA,
        "schema_version": expected.get("schema_version") == actual.get("schema_version"),
        "database_logical_sha256": bool(expected.get("database", {}).get("logical_sha256")) and expected.get("database", {}).get("logical_sha256") == actual.get("database", {}).get("logical_sha256"),
        "storage_tree_sha256": bool(expected.get("storage", {}).get("tree_sha256")) and expected.get("storage", {}).get("tree_sha256") == actual.get("storage", {}).get("tree_sha256"),
        "actual_integrity": actual.get("status") == "pass" and int(actual.get("critical_findings") or 0) == 0,
    }
    status = "pass" if all(checks.values()) else "fail"
    return {
        "schema": "mgc.authoritative-consistency-compare.v1",
        "status": status,
        "checks": checks,
        "expected_epoch_id": expected.get("epoch_id"),
        "expected_database_sha256": expected.get("database", {}).get("logical_sha256"),
        "actual_database_sha256": actual.get("database", {}).get("logical_sha256"),
        "expected_storage_sha256": expected.get("storage", {}).get("tree_sha256"),
        "actual_storage_sha256": actual.get("storage", {}).get("tree_sha256"),
        "actual_critical_findings": actual.get("critical_findings"),
    }


def postgres_pitr_status(db: Session) -> dict[str, Any]:
    """Return a sanitized PostgreSQL PITR posture without exposing archive_command content."""
    conn = db.connection()
    if conn.dialect.name != "postgresql":
        return {"engine": conn.dialect.name, "supported": False, "pitr_ready": False}
    out: dict[str, Any] = {"engine": "postgresql", "supported": True}
    try:
        out["wal_level"] = conn.execute(text("SHOW wal_level")).scalar_one()
        out["archive_mode"] = conn.execute(text("SHOW archive_mode")).scalar_one()
        out["archive_timeout"] = conn.execute(text("SHOW archive_timeout")).scalar_one()
        out["checkpoint_lsn"] = conn.execute(text("SELECT pg_current_wal_lsn()::text")).scalar_one()
        out["in_recovery"] = bool(conn.execute(text("SELECT pg_is_in_recovery()")).scalar_one())
        command = str(conn.execute(text("SHOW archive_command")).scalar_one() or "")
        out["archive_command_configured"] = bool(command.strip()) and command.strip() not in {"(disabled)", ""}
        out["pitr_ready"] = out["wal_level"] in {"replica", "logical"} and out["archive_mode"] in {"on", "always"} and out["archive_command_configured"]
    except Exception as exc:
        out["pitr_ready"] = False
        out["probe_error"] = type(exc).__name__
    return out
