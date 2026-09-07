from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.release_provenance import (
    CANONICALIZATION,
    PROVENANCE_REGISTRY_SCHEMA,
    ProvenanceError,
    append_event,
    build_audit_report,
    event_sha256,
    load_events,
    parse_utc,
    read_object,
    registry_paths,
    registry_summary,
    replay_trust_state,
    sha256_bytes,
    sha256_file,
    store_object,
    utcnow_iso,
    verify_registry,
)

RETENTION_POLICY_SCHEMA = "mgc-release-retention-policy-v1"
CHECKPOINT_SCHEMA = "mgc-release-provenance-checkpoint-v1"
ANCHOR_REQUEST_SCHEMA = "mgc-release-anchor-request-v1"
ANCHOR_RECEIPT_SCHEMA = "mgc-release-anchor-receipt-v1"
WORM_REQUEST_SCHEMA = "mgc-release-worm-request-v1"
WORM_RECEIPT_SCHEMA = "mgc-release-worm-receipt-v1"
AUDITOR_BUNDLE_SCHEMA = "mgc-release-auditor-bundle-v1"
GOVERNANCE_SCHEMA = "mgc-release-provenance-governance-v1"

DEFAULT_RETENTION_DAYS = {
    "registry_event": 3650,
    "acceptance": 3650,
    "baseline": 3650,
    "load": 1095,
    "failover": 3650,
    "public_key": 3650,
    "checkpoint": 3650,
    "anchor_receipt": 3650,
    "worm_receipt": 3650,
}


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _parse_command_json(command_json: str | list[str]) -> list[str]:
    if isinstance(command_json, list):
        command = command_json
    else:
        try:
            command = json.loads(command_json)
        except json.JSONDecodeError as exc:
            raise ProvenanceError("adapter command must be a JSON array of argv strings") from exc
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise ProvenanceError("adapter command must be a non-empty JSON array of argv strings")
    if len(command) > 32 or any(len(x) > 2048 for x in command):
        raise ProvenanceError("adapter command exceeds governance safety limits")
    return command


def run_json_adapter(command_json: str | list[str], request: dict[str, Any], *, timeout_seconds: int = 30) -> dict[str, Any]:
    command = _parse_command_json(command_json)
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}}
    proc = subprocess.run(
        command,
        input=json.dumps(request, ensure_ascii=False, sort_keys=True),
        text=True,
        capture_output=True,
        timeout=max(1, min(int(timeout_seconds), 300)),
        env=env,
        shell=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "adapter failed").strip()[:300]
        raise ProvenanceError(f"external governance adapter failed: {detail}")
    try:
        response = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ProvenanceError("external governance adapter returned invalid JSON") from exc
    if not isinstance(response, dict):
        raise ProvenanceError("external governance adapter response must be an object")
    return response


def set_retention_policy(
    root: str | Path,
    *,
    policy_id: str,
    retention_days: dict[str, int] | None = None,
    actor: str = "release-governance",
) -> dict[str, Any]:
    if not str(policy_id).strip() or len(str(policy_id)) > 128:
        raise ProvenanceError("policy_id is required and must be <=128 chars")
    merged = dict(DEFAULT_RETENTION_DAYS)
    for kind, value in (retention_days or {}).items():
        if kind not in merged:
            raise ProvenanceError(f"unsupported retention kind: {kind}")
        days = int(value)
        if days < 1:
            raise ProvenanceError("retention days must be positive")
        merged[kind] = days
    payload = {
        "schema": RETENTION_POLICY_SCHEMA,
        "policy_id": str(policy_id),
        "retention_days": merged,
        "automatic_deletion": False,
        "ledger_metadata_permanent": True,
        "destruction_requires_external_governance": True,
    }
    return append_event(root, event_type="RETENTION_POLICY_SET", actor=actor, payload=payload)


def place_legal_hold(
    root: str | Path,
    *,
    hold_id: str,
    reason: str,
    release: str | None = None,
    object_sha256: str | None = None,
    actor: str = "release-governance",
) -> dict[str, Any]:
    hold_id = str(hold_id).strip()
    if not hold_id or len(hold_id) > 128:
        raise ProvenanceError("hold_id is required and must be <=128 chars")
    if not str(reason).strip():
        raise ProvenanceError("legal hold reason is required")
    if not release and not object_sha256:
        raise ProvenanceError("legal hold must target a release or object_sha256")
    if object_sha256 and (len(object_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in object_sha256)):
        raise ProvenanceError("invalid legal hold object SHA-256")
    state = replay_governance_state(root)
    if hold_id in state["holds"] and state["holds"][hold_id]["status"] == "ACTIVE":
        raise ProvenanceError("legal hold is already active")
    return append_event(
        root,
        event_type="LEGAL_HOLD_PLACED",
        actor=actor,
        payload={
            "hold_id": hold_id,
            "reason": str(reason)[:1000],
            "release": release,
            "object_sha256": object_sha256.lower() if object_sha256 else None,
        },
    )


def release_legal_hold(root: str | Path, *, hold_id: str, reason: str, actor: str = "release-governance") -> dict[str, Any]:
    state = replay_governance_state(root)
    hold = state["holds"].get(str(hold_id))
    if not hold or hold.get("status") != "ACTIVE":
        raise ProvenanceError("only an active legal hold can be released")
    if not str(reason).strip():
        raise ProvenanceError("legal hold release reason is required")
    return append_event(
        root,
        event_type="LEGAL_HOLD_RELEASED",
        actor=actor,
        payload={"hold_id": str(hold_id), "reason": str(reason)[:1000]},
    )


def replay_governance_state(root: str | Path) -> dict[str, Any]:
    policy: dict[str, Any] | None = None
    holds: dict[str, dict[str, Any]] = {}
    checkpoints: list[dict[str, Any]] = []
    anchors: list[dict[str, Any]] = []
    worm_receipts: list[dict[str, Any]] = []
    for event in load_events(root):
        et = event.get("event_type")
        payload = copy.deepcopy(event.get("payload") or {})
        payload["sequence"] = event.get("sequence")
        payload["recorded_at"] = event.get("recorded_at")
        if et == "RETENTION_POLICY_SET":
            policy = payload
        elif et == "LEGAL_HOLD_PLACED":
            payload["status"] = "ACTIVE"
            holds[str(payload.get("hold_id"))] = payload
        elif et == "LEGAL_HOLD_RELEASED":
            hold_id = str(payload.get("hold_id"))
            if hold_id in holds:
                holds[hold_id]["status"] = "RELEASED"
                holds[hold_id]["released_sequence"] = event.get("sequence")
                holds[hold_id]["release_reason"] = payload.get("reason")
        elif et == "CHECKPOINT_CREATED":
            checkpoints.append(payload)
        elif et == "EXTERNAL_ANCHOR_RECORDED":
            anchors.append(payload)
        elif et == "WORM_RECEIPT_RECORDED":
            worm_receipts.append(payload)
    return {
        "policy": policy,
        "holds": holds,
        "checkpoints": checkpoints,
        "anchors": anchors,
        "worm_receipts": worm_receipts,
    }


def key_lifecycle_status(root: str | Path, *, now: datetime | None = None, default_warning_days: int = 30) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    trust = replay_trust_state(load_events(root))
    rows: list[dict[str, Any]] = []
    for key_id, state in sorted(trust.items()):
        status = str(state.get("status") or "UNKNOWN")
        expiry = parse_utc(state.get("expires_at"))
        warning_days = int(state.get("rotation_warning_days") or default_warning_days)
        days_remaining: float | None = None
        lifecycle = status
        if status == "ACTIVE" and expiry is not None:
            days_remaining = (expiry - now).total_seconds() / 86400.0
            if days_remaining <= 0:
                lifecycle = "EXPIRED"
            elif days_remaining <= warning_days:
                lifecycle = "ROTATION_DUE"
        rows.append({
            "key_id": key_id,
            "lifecycle": lifecycle,
            "expires_at": state.get("expires_at"),
            "days_remaining": None if days_remaining is None else round(days_remaining, 2),
            "revoked_sequence": state.get("revoked_sequence"),
        })
    active_usable = [r for r in rows if r["lifecycle"] in {"ACTIVE", "ROTATION_DUE"}]
    return {
        "keys": rows,
        "active_usable_keys": len(active_usable),
        "expired_key_ids": [r["key_id"] for r in rows if r["lifecycle"] == "EXPIRED"],
        "rotation_due_key_ids": [r["key_id"] for r in rows if r["lifecycle"] == "ROTATION_DUE"],
    }


def retention_status(root: str | Path, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    state = replay_governance_state(root)
    active_holds = [v for v in state["holds"].values() if v.get("status") == "ACTIVE"]
    return {
        "schema": RETENTION_POLICY_SCHEMA,
        "policy": copy.deepcopy(state["policy"]),
        "policy_configured": state["policy"] is not None,
        "active_legal_holds": len(active_holds),
        "active_hold_ids": sorted(str(v.get("hold_id")) for v in active_holds),
        "automatic_deletion": False,
        "ledger_metadata_permanent": True,
        "evaluated_at": now.isoformat().replace("+00:00", "Z"),
    }


def create_checkpoint(root: str | Path, *, actor: str = "release-governance") -> dict[str, Any]:
    verification = verify_registry(root)
    if verification.get("status") != "PASS":
        raise ProvenanceError("registry must verify before checkpointing")
    summary = registry_summary(root)
    retention = retention_status(root)
    keys = key_lifecycle_status(root)
    checkpoint = {
        "schema": CHECKPOINT_SCHEMA,
        "created_at": utcnow_iso(),
        "covered_tip_sequence": verification.get("tip_sequence"),
        "covered_tip_sha256": verification.get("tip_sha256"),
        "registry_status": verification.get("status"),
        "summary": summary,
        "retention": retention,
        "key_lifecycle": keys,
        "production_authorized": False,
    }
    checkpoint["integrity"] = {
        "canonicalization": CANONICALIZATION,
        "canonical_sha256": sha256_bytes(_canonical_json_bytes(checkpoint)),
    }
    data = (json.dumps(checkpoint, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    obj = store_object(root, data)
    return append_event(
        root,
        event_type="CHECKPOINT_CREATED",
        actor=actor,
        payload={
            "checkpoint_object_sha256": obj["sha256"],
            "covered_tip_sequence": verification.get("tip_sequence"),
            "covered_tip_sha256": verification.get("tip_sha256"),
            "checkpoint_canonical_sha256": checkpoint["integrity"]["canonical_sha256"],
        },
        objects=[{"kind": "checkpoint", **obj}],
    )


def record_external_anchor(
    root: str | Path,
    *,
    command_json: str | list[str],
    actor: str = "release-governance",
    provider: str = "external",
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    verification = verify_registry(root)
    if verification.get("status") != "PASS":
        raise ProvenanceError("registry must verify before external anchoring")
    request = {
        "schema": ANCHOR_REQUEST_SCHEMA,
        "provider": str(provider)[:128],
        "requested_at": utcnow_iso(),
        "tip_sequence": verification["tip_sequence"],
        "tip_sha256": verification["tip_sha256"],
    }
    response = run_json_adapter(command_json, request, timeout_seconds=timeout_seconds)
    if response.get("status") not in {"ANCHORED", "STORED", "OK"}:
        raise ProvenanceError("external anchor adapter did not confirm storage")
    if int(response.get("tip_sequence") or -1) != int(request["tip_sequence"]):
        raise ProvenanceError("external anchor receipt sequence mismatch")
    if str(response.get("tip_sha256") or "").lower() != str(request["tip_sha256"] or "").lower():
        raise ProvenanceError("external anchor receipt hash mismatch")
    receipt = {
        "schema": ANCHOR_RECEIPT_SCHEMA,
        "provider": str(response.get("provider") or provider)[:128],
        "anchor_id": str(response.get("anchor_id") or response.get("receipt_id") or "")[:256],
        "anchored_at": str(response.get("anchored_at") or utcnow_iso()),
        "tip_sequence": request["tip_sequence"],
        "tip_sha256": request["tip_sha256"],
        "provider_receipt": response.get("receipt"),
    }
    if not receipt["anchor_id"]:
        raise ProvenanceError("external anchor receipt requires anchor_id")
    req_obj = store_object(root, _canonical_json_bytes(request))
    receipt_obj = store_object(root, _canonical_json_bytes(receipt))
    return append_event(
        root,
        event_type="EXTERNAL_ANCHOR_RECORDED",
        actor=actor,
        payload={
            "provider": receipt["provider"],
            "anchor_id": receipt["anchor_id"],
            "anchored_tip_sequence": request["tip_sequence"],
            "anchored_tip_sha256": request["tip_sha256"],
            "anchor_receipt_object_sha256": receipt_obj["sha256"],
        },
        objects=[{"kind": "anchor_request", **req_obj}, {"kind": "anchor_receipt", **receipt_obj}],
    )


def seal_latest_checkpoint_to_worm(
    root: str | Path,
    *,
    command_json: str | list[str],
    retain_days: int = 3650,
    lock_mode: str = "COMPLIANCE",
    actor: str = "release-governance",
    provider: str = "external-worm",
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    state = replay_governance_state(root)
    if not state["checkpoints"]:
        raise ProvenanceError("create a registry checkpoint before WORM sealing")
    cp = state["checkpoints"][-1]
    digest = str(cp.get("checkpoint_object_sha256") or "")
    data = read_object(root, digest)
    mode = str(lock_mode).upper()
    if mode not in {"COMPLIANCE", "GOVERNANCE"}:
        raise ProvenanceError("WORM lock mode must be COMPLIANCE or GOVERNANCE")
    if int(retain_days) < 1:
        raise ProvenanceError("WORM retain_days must be positive")
    retain_until = (datetime.now(timezone.utc) + timedelta(days=int(retain_days))).isoformat().replace("+00:00", "Z")
    request = {
        "schema": WORM_REQUEST_SCHEMA,
        "provider": str(provider)[:128],
        "requested_at": utcnow_iso(),
        "object_sha256": digest,
        "object_size_bytes": len(data),
        "retain_until": retain_until,
        "lock_mode": mode,
        "legal_hold": retention_status(root)["active_legal_holds"] > 0,
    }
    response = run_json_adapter(command_json, request, timeout_seconds=timeout_seconds)
    if response.get("status") not in {"LOCKED", "STORED", "OK"}:
        raise ProvenanceError("WORM adapter did not confirm object lock")
    if str(response.get("object_sha256") or "").lower() != digest.lower():
        raise ProvenanceError("WORM receipt object hash mismatch")
    receipt_retain_until = parse_utc(str(response.get("retain_until") or ""))
    requested_until = parse_utc(retain_until)
    if receipt_retain_until is None or requested_until is None or receipt_retain_until < requested_until:
        raise ProvenanceError("WORM receipt retention is shorter than requested")
    receipt = {
        "schema": WORM_RECEIPT_SCHEMA,
        "provider": str(response.get("provider") or provider)[:128],
        "receipt_id": str(response.get("receipt_id") or response.get("object_lock_id") or "")[:256],
        "object_sha256": digest,
        "retain_until": receipt_retain_until.isoformat().replace("+00:00", "Z"),
        "lock_mode": str(response.get("lock_mode") or mode).upper(),
        "confirmed_at": str(response.get("confirmed_at") or utcnow_iso()),
        "provider_receipt": response.get("receipt"),
    }
    if not receipt["receipt_id"]:
        raise ProvenanceError("WORM receipt requires receipt_id")
    req_obj = store_object(root, _canonical_json_bytes(request))
    receipt_obj = store_object(root, _canonical_json_bytes(receipt))
    return append_event(
        root,
        event_type="WORM_RECEIPT_RECORDED",
        actor=actor,
        payload={
            "provider": receipt["provider"],
            "receipt_id": receipt["receipt_id"],
            "checkpoint_object_sha256": digest,
            "retain_until": receipt["retain_until"],
            "lock_mode": receipt["lock_mode"],
            "worm_receipt_object_sha256": receipt_obj["sha256"],
        },
        objects=[{"kind": "worm_request", **req_obj}, {"kind": "worm_receipt", **receipt_obj}],
    )


def _find_event_hash_at_sequence(root: str | Path, sequence: int) -> str | None:
    for event in load_events(root):
        if int(event.get("sequence") or 0) == int(sequence):
            return event_sha256(event)
    return None


def verify_governance(
    root: str | Path,
    *,
    require_external_anchor: bool = False,
    require_worm_receipt: bool = False,
    anchor_max_age_hours: int = 24,
    checkpoint_max_age_hours: int = 24,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    registry = verify_registry(root)
    if registry.get("status") != "PASS":
        return {
            "schema": GOVERNANCE_SCHEMA,
            "status": "FAIL",
            "registry_status": registry.get("status"),
            "failures": ["registry_integrity"],
            "warnings": [],
            "production_authorized": False,
        }
    state = replay_governance_state(root)
    keys = key_lifecycle_status(root, now=now)
    retention = retention_status(root, now=now)
    failures: list[str] = []
    warnings: list[str] = []
    if not retention["policy_configured"]:
        warnings.append("retention_policy_missing")
    if keys["active_usable_keys"] < 1:
        failures.append("no_usable_signing_key")
    if keys["expired_key_ids"]:
        warnings.append("expired_keys_present")
    if keys["rotation_due_key_ids"]:
        warnings.append("key_rotation_due")
    latest_anchor = state["anchors"][-1] if state["anchors"] else None
    anchor_fresh = False
    if latest_anchor:
        seq = int(latest_anchor.get("anchored_tip_sequence") or 0)
        expected = _find_event_hash_at_sequence(root, seq)
        if not expected or expected.lower() != str(latest_anchor.get("anchored_tip_sha256") or "").lower():
            failures.append("external_anchor_chain_mismatch")
        try:
            receipt = json.loads(read_object(root, str(latest_anchor.get("anchor_receipt_object_sha256") or "")).decode("utf-8"))
            if receipt.get("schema") != ANCHOR_RECEIPT_SCHEMA:
                failures.append("external_anchor_receipt_schema")
            if int(receipt.get("tip_sequence") or -1) != seq or str(receipt.get("tip_sha256") or "").lower() != str(latest_anchor.get("anchored_tip_sha256") or "").lower():
                failures.append("external_anchor_receipt_mismatch")
        except (ProvenanceError, UnicodeDecodeError, json.JSONDecodeError):
            failures.append("external_anchor_receipt_invalid")
        at = parse_utc(latest_anchor.get("recorded_at"))
        if at is not None:
            age_hours = (now - at).total_seconds() / 3600.0
            anchor_fresh = age_hours <= max(1, int(anchor_max_age_hours))
            if not anchor_fresh:
                warnings.append("external_anchor_stale")
    else:
        warnings.append("external_anchor_missing")
    if require_external_anchor and (latest_anchor is None or not anchor_fresh):
        failures.append("required_external_anchor_unavailable")
    latest_worm = state["worm_receipts"][-1] if state["worm_receipts"] else None
    if latest_worm is None:
        warnings.append("worm_receipt_missing")
    else:
        try:
            receipt = json.loads(read_object(root, str(latest_worm.get("worm_receipt_object_sha256") or "")).decode("utf-8"))
            if receipt.get("schema") != WORM_RECEIPT_SCHEMA:
                failures.append("worm_receipt_schema")
            if str(receipt.get("object_sha256") or "").lower() != str(latest_worm.get("checkpoint_object_sha256") or "").lower():
                failures.append("worm_receipt_object_mismatch")
            retain_until = parse_utc(receipt.get("retain_until"))
            if retain_until is None or retain_until <= now:
                failures.append("worm_retention_expired")
        except (ProvenanceError, UnicodeDecodeError, json.JSONDecodeError):
            failures.append("worm_receipt_invalid")
    if require_worm_receipt and latest_worm is None:
        failures.append("required_worm_receipt_unavailable")
    checkpoint_fresh = False
    if not state["checkpoints"]:
        warnings.append("checkpoint_missing")
    else:
        cp_at = parse_utc(state["checkpoints"][-1].get("recorded_at"))
        if cp_at is not None:
            cp_age = (now - cp_at).total_seconds() / 3600.0
            checkpoint_fresh = cp_age <= max(1, int(checkpoint_max_age_hours))
            if not checkpoint_fresh:
                warnings.append("checkpoint_stale")
    status = "FAIL" if failures else ("CONDITIONAL" if warnings else "PASS")
    return {
        "schema": GOVERNANCE_SCHEMA,
        "status": status,
        "registry_status": "PASS",
        "tip_sequence": registry.get("tip_sequence"),
        "tip_sha256": registry.get("tip_sha256"),
        "retention": retention,
        "key_lifecycle": keys,
        "checkpoint_count": len(state["checkpoints"]),
        "checkpoint_fresh": checkpoint_fresh,
        "external_anchor": None if latest_anchor is None else {
            "provider": latest_anchor.get("provider"),
            "anchor_id": latest_anchor.get("anchor_id"),
            "anchored_tip_sequence": latest_anchor.get("anchored_tip_sequence"),
            "recorded_at": latest_anchor.get("recorded_at"),
            "fresh": anchor_fresh,
        },
        "worm": None if latest_worm is None else {
            "provider": latest_worm.get("provider"),
            "receipt_id": latest_worm.get("receipt_id"),
            "retain_until": latest_worm.get("retain_until"),
            "lock_mode": latest_worm.get("lock_mode"),
        },
        "failures": failures,
        "warnings": warnings,
        "production_authorized": False,
    }


def export_auditor_bundle(root: str | Path, *, output: str | Path) -> dict[str, Any]:
    verification = verify_registry(root)
    if verification.get("status") != "PASS":
        raise ProvenanceError("registry must verify before auditor bundle export")
    root_path = registry_paths(root).root
    output_path = Path(output).expanduser().absolute()
    if output_path.exists() or output_path.is_symlink():
        raise ProvenanceError("auditor bundle output already exists")
    audit = build_audit_report(root)
    governance = verify_governance(root)
    files: dict[str, bytes] = {}
    for event in sorted((root_path / "events").glob("*.json")):
        if event.is_symlink():
            raise ProvenanceError("symlink forbidden during auditor export")
        files[f"registry/events/{event.name}"] = event.read_bytes()
    object_dir = root_path / "objects" / "sha256"
    for obj in sorted(object_dir.iterdir() if object_dir.exists() else []):
        if obj.is_symlink() or not obj.is_file():
            raise ProvenanceError("invalid registry object during auditor export")
        data = obj.read_bytes()
        if sha256_bytes(data) != obj.name:
            raise ProvenanceError("corrupt registry object during auditor export")
        files[f"registry/objects/sha256/{obj.name}"] = data
    files["audit-report.json"] = (json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    files["governance-status.json"] = (json.dumps(governance, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    manifest_entries = [
        {"path": name, "size_bytes": len(data), "sha256": sha256_bytes(data)} for name, data in sorted(files.items())
    ]
    manifest = {
        "schema": AUDITOR_BUNDLE_SCHEMA,
        "created_at": utcnow_iso(),
        "registry_tip_sequence": verification.get("tip_sequence"),
        "registry_tip_sha256": verification.get("tip_sha256"),
        "files": manifest_entries,
        "private_keys_included": False,
        "production_authorized": False,
    }
    files["bundle-manifest.json"] = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.external_attr = (0o100440 & 0xFFFF) << 16
            zf.writestr(info, data)
    return {
        "schema": AUDITOR_BUNDLE_SCHEMA,
        "status": "PASS",
        "output": str(output_path),
        "bundle_sha256": sha256_file(output_path),
        "files": len(files),
        "registry_tip_sequence": verification.get("tip_sequence"),
        "registry_tip_sha256": verification.get("tip_sha256"),
        "production_authorized": False,
    }


def verify_auditor_bundle(bundle: str | Path) -> dict[str, Any]:
    path = Path(bundle).expanduser().absolute()
    if path.is_symlink() or not path.is_file():
        raise ProvenanceError("auditor bundle must be a regular file")
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mgc-auditor-bundle-") as td:
        dest = Path(td)
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            if len(names) != len(set(names)):
                failures.append("duplicate_zip_member")
            for info in zf.infolist():
                pp = PurePosixPath(info.filename)
                if pp.is_absolute() or ".." in pp.parts or info.filename.endswith("/"):
                    failures.append("unsafe_zip_member")
                    continue
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    failures.append("symlink_zip_member")
                    continue
                target = dest.joinpath(*pp.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(info))
        manifest_path = dest / "bundle-manifest.json"
        if not manifest_path.is_file():
            failures.append("manifest_missing")
            manifest = {"files": []}
        else:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                failures.append("manifest_invalid_json")
                manifest = {"files": []}
        if manifest.get("schema") != AUDITOR_BUNDLE_SCHEMA:
            failures.append("manifest_schema")
        expected_paths = {str(row.get("path")) for row in manifest.get("files") or []}
        actual_paths = {
            str(p.relative_to(dest).as_posix()) for p in dest.rglob("*") if p.is_file() and p.name != "bundle-manifest.json"
        }
        if expected_paths != actual_paths:
            failures.append("manifest_file_set")
        for row in manifest.get("files") or []:
            rel = str(row.get("path") or "")
            f = dest / rel
            if not f.is_file():
                failures.append(f"missing:{rel}")
                continue
            data = f.read_bytes()
            if len(data) != int(row.get("size_bytes") or -1):
                failures.append(f"size:{rel}")
            if sha256_bytes(data) != str(row.get("sha256") or ""):
                failures.append(f"hash:{rel}")
        if not failures:
            reg = verify_registry(dest / "registry")
            if reg.get("status") != "PASS":
                failures.append("registry_replay")
            if int(reg.get("tip_sequence") or 0) != int(manifest.get("registry_tip_sequence") or -1):
                failures.append("tip_sequence")
            if str(reg.get("tip_sha256") or "") != str(manifest.get("registry_tip_sha256") or ""):
                failures.append("tip_hash")
    return {
        "schema": AUDITOR_BUNDLE_SCHEMA,
        "status": "PASS" if not failures else "FAIL",
        "bundle_sha256": sha256_file(path),
        "failures": failures,
        "production_authorized": False,
    }
