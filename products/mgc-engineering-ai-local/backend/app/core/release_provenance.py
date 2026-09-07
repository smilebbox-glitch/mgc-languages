from __future__ import annotations

import copy
import hashlib
import fcntl
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from app.core.load_certification import LOAD_EVIDENCE_SCHEMA, canonical_payload_bytes as load_canonical_bytes, validate_integrity as validate_load_integrity
from app.core.release_acceptance import (
    APPROVED_BASELINE_SCHEMA,
    RELEASE_ACCEPTANCE_SCHEMA,
    canonical_payload_bytes as acceptance_canonical_bytes,
    validate_integrity as validate_acceptance_integrity,
)

PROVENANCE_EVENT_SCHEMA = "mgc-release-provenance-event-v1"
PROVENANCE_REGISTRY_SCHEMA = "mgc-release-provenance-registry-v1"
PROVENANCE_AUDIT_SCHEMA = "mgc-release-provenance-audit-v1"
CANONICALIZATION = "mgc-json-sorted-utf8-v1"
EVENT_TYPES = {
    "REGISTRY_INITIALIZED",
    "KEY_REGISTERED",
    "KEY_REVOKED",
    "ACCEPTANCE_REGISTERED",
    "BASELINE_REGISTERED",
    "LOAD_EVIDENCE_REGISTERED",
    "FAILOVER_EVIDENCE_REGISTERED",
    "RETENTION_POLICY_SET",
    "LEGAL_HOLD_PLACED",
    "LEGAL_HOLD_RELEASED",
    "CHECKPOINT_CREATED",
    "EXTERNAL_ANCHOR_RECORDED",
    "WORM_RECEIPT_RECORDED",
}
KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ProvenanceError(ValueError):
    pass


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProvenanceError(f"invalid UTC timestamp: {value}") from exc
    if dt.tzinfo is None:
        raise ProvenanceError("timestamp must include timezone")
    return dt.astimezone(timezone.utc)


def iso_after_days(days: int, *, base: datetime | None = None) -> str:
    if int(days) <= 0:
        raise ProvenanceError("validity days must be positive")
    dt = (base or datetime.now(timezone.utc)) + timedelta(days=int(days))
    return dt.isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_event_bytes(event: dict[str, Any]) -> bytes:
    payload = copy.deepcopy(event)
    payload.pop("integrity", None)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def event_sha256(event: dict[str, Any]) -> str:
    return sha256_bytes(canonical_event_bytes(event))


def validate_event_integrity(event: dict[str, Any]) -> tuple[bool | None, str | None, str]:
    integ = event.get("integrity") or {}
    claimed = integ.get("canonical_sha256")
    actual = event_sha256(event)
    if not claimed:
        return None, None, actual
    return str(claimed).lower() == actual.lower(), str(claimed), actual


def attach_event_integrity(event: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(event)
    out["integrity"] = {
        "canonicalization": CANONICALIZATION,
        "canonical_sha256": event_sha256(out),
    }
    return out


def _ensure_no_symlink(path: Path, *, allow_missing_leaf: bool = False) -> None:
    absolute = path.absolute()
    parts = absolute.parts
    cursor = Path(parts[0]) if parts else Path("/")
    for idx, part in enumerate(parts[1:], start=1):
        cursor = cursor / part
        if not cursor.exists():
            if allow_missing_leaf and idx == len(parts) - 1:
                return
            continue
        if cursor.is_symlink():
            raise ProvenanceError(f"symlink is forbidden in provenance path: {cursor}")


def _atomic_write(path: Path, data: bytes, *, mode: int = 0o640) -> None:
    _ensure_no_symlink(path.parent)
    if path.exists() or path.is_symlink():
        raise ProvenanceError(f"immutable provenance path already exists: {path.name}")
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temp, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.close(fd)
        fd = -1
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        temp.unlink(missing_ok=True)


@dataclass(frozen=True)
class RegistryPaths:
    root: Path
    events: Path
    objects: Path


def registry_paths(root: str | Path) -> RegistryPaths:
    p = Path(root).expanduser().absolute()
    return RegistryPaths(root=p, events=p / "events", objects=p / "objects" / "sha256")


def ensure_registry_dirs(root: str | Path) -> RegistryPaths:
    rp = registry_paths(root)
    _ensure_no_symlink(rp.root, allow_missing_leaf=True)
    rp.events.mkdir(parents=True, exist_ok=True, mode=0o750)
    rp.objects.mkdir(parents=True, exist_ok=True, mode=0o750)
    _ensure_no_symlink(rp.root)
    return rp


class _AppendLock:
    def __init__(self, root: str | Path):
        self.rp = ensure_registry_dirs(root)
        self.path = self.rp.root / ".append.lock"
        self.fd: int | None = None

    def __enter__(self):
        _ensure_no_symlink(self.rp.root)
        if self.path.is_symlink():
            raise ProvenanceError("symlink append lock is forbidden")
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


def object_path(root: str | Path, digest: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", str(digest).lower()):
        raise ProvenanceError("invalid SHA-256 object digest")
    rp = registry_paths(root)
    return rp.objects / str(digest).lower()


def store_object(root: str | Path, data: bytes) -> dict[str, Any]:
    rp = ensure_registry_dirs(root)
    digest = sha256_bytes(data)
    dest = rp.objects / digest
    if dest.exists():
        _ensure_no_symlink(dest)
        if not dest.is_file() or sha256_file(dest) != digest:
            raise ProvenanceError("content-addressed object collision or corruption")
    else:
        _atomic_write(dest, data, mode=0o440)
    return {"sha256": digest, "size_bytes": len(data)}


def read_object(root: str | Path, digest: str) -> bytes:
    p = object_path(root, digest)
    _ensure_no_symlink(p)
    if not p.is_file():
        raise ProvenanceError(f"missing provenance object {digest}")
    data = p.read_bytes()
    if sha256_bytes(data) != str(digest).lower():
        raise ProvenanceError(f"provenance object hash mismatch {digest}")
    return data


def _event_files(root: str | Path) -> list[Path]:
    rp = registry_paths(root)
    if not rp.events.exists():
        return []
    _ensure_no_symlink(rp.events)
    files = [p for p in rp.events.iterdir() if p.is_file() and re.fullmatch(r"\d{8}-[0-9a-f]{64}\.json", p.name)]
    return sorted(files, key=lambda p: p.name)


def load_events(root: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in _event_files(root):
        _ensure_no_symlink(p)
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise ProvenanceError(f"invalid registry event JSON: {p.name}") from exc
    return rows


def verify_event_chain(root: str | Path, *, verify_objects: bool = True) -> dict[str, Any]:
    events = load_events(root)
    prev: str | None = None
    expected_seq = 1
    failures: list[dict[str, Any]] = []
    object_count = 0
    seen_objects: set[str] = set()
    files = _event_files(root)
    for file_path, event in zip(files, events):
        reasons: list[str] = []
        valid, _claimed, actual = validate_event_integrity(event)
        expected_name = f"{expected_seq:08d}-{actual}.json"
        if file_path.name != expected_name:
            reasons.append("filename")
        if event.get("schema") != PROVENANCE_EVENT_SCHEMA:
            reasons.append("schema")
        if event.get("event_type") not in EVENT_TYPES:
            reasons.append("event_type")
        if valid is not True:
            reasons.append("digest")
        if int(event.get("sequence") or 0) != expected_seq:
            reasons.append("sequence")
        if event.get("parent_event_sha256") != prev:
            reasons.append("parent")
        refs = event.get("objects") or []
        if not isinstance(refs, list):
            reasons.append("objects")
            refs = []
        if verify_objects:
            for ref in refs:
                digest = str((ref or {}).get("sha256") or "").lower()
                try:
                    data = read_object(root, digest)
                    if int((ref or {}).get("size_bytes") or -1) != len(data):
                        reasons.append(f"object_size:{digest[:12]}")
                    if digest not in seen_objects:
                        seen_objects.add(digest); object_count += 1
                except ProvenanceError:
                    reasons.append(f"object:{digest[:12] or 'missing'}")
        if reasons:
            failures.append({"sequence": event.get("sequence"), "event_type": event.get("event_type"), "reasons": reasons})
        prev = actual
        expected_seq += 1
    return {
        "schema": PROVENANCE_REGISTRY_SCHEMA,
        "status": "PASS" if not failures else "FAIL",
        "events": len(events),
        "objects": object_count,
        "tip_sequence": len(events),
        "tip_sha256": prev,
        "failures": failures,
    }


def replay_trust_state(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    keys: dict[str, dict[str, Any]] = {}
    for e in events:
        et = e.get("event_type")
        payload = e.get("payload") or {}
        if et == "KEY_REGISTERED":
            key_id = str(payload.get("key_id") or "")
            keys[key_id] = {
                "key_id": key_id,
                "status": "ACTIVE",
                "public_key_object_sha256": payload.get("public_key_object_sha256"),
                "public_key_sha256": payload.get("public_key_sha256"),
                "algorithm": payload.get("algorithm"),
                "not_before": payload.get("not_before"),
                "expires_at": payload.get("expires_at"),
                "rotation_warning_days": int(payload.get("rotation_warning_days") or 30),
                "registered_at": e.get("recorded_at"),
                "registered_sequence": e.get("sequence"),
                "revoked_sequence": None,
                "revocation_reason": None,
            }
        elif et == "KEY_REVOKED":
            key_id = str(payload.get("key_id") or "")
            if key_id in keys:
                keys[key_id]["status"] = "REVOKED"
                keys[key_id]["revoked_sequence"] = e.get("sequence")
                keys[key_id]["revocation_reason"] = payload.get("reason")
    return keys


def _head(root: str | Path) -> tuple[int, str | None]:
    verification = verify_event_chain(root, verify_objects=False)
    if verification["status"] != "PASS":
        raise ProvenanceError("registry chain is invalid; refuse append")
    return int(verification["tip_sequence"]), verification["tip_sha256"]


def append_event(root: str | Path, *, event_type: str, payload: dict[str, Any], objects: list[dict[str, Any]] | None = None, actor: str = "release-engineering", recorded_at: str | None = None) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ProvenanceError(f"unsupported provenance event type: {event_type}")
    rp = ensure_registry_dirs(root)
    with _AppendLock(root):
        seq, parent = _head(root)
        if seq == 0 and event_type != "REGISTRY_INITIALIZED":
            raise ProvenanceError("first registry event must be REGISTRY_INITIALIZED")
        if seq > 0 and event_type == "REGISTRY_INITIALIZED":
            raise ProvenanceError("registry initialization event already exists")
        event = {
            "schema": PROVENANCE_EVENT_SCHEMA,
            "sequence": seq + 1,
            "event_type": event_type,
            "recorded_at": recorded_at or utcnow_iso(),
            "actor": str(actor)[:160],
            "parent_event_sha256": parent,
            "payload": copy.deepcopy(payload),
            "objects": copy.deepcopy(objects or []),
        }
        event = attach_event_integrity(event)
        digest = event["integrity"]["canonical_sha256"]
        path = rp.events / f"{seq + 1:08d}-{digest}.json"
        _atomic_write(path, (json.dumps(event, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"), mode=0o440)
        return event


def initialize_registry(root: str | Path, *, registry_id: str, actor: str = "release-engineering") -> dict[str, Any]:
    if not registry_id or len(registry_id) > 128:
        raise ProvenanceError("registry_id is required and must be <= 128 chars")
    ensure_registry_dirs(root)
    if load_events(root):
        raise ProvenanceError("registry already contains events")
    return append_event(root, event_type="REGISTRY_INITIALIZED", actor=actor, payload={"registry_id": registry_id, "format": PROVENANCE_REGISTRY_SCHEMA})


def _validate_key_id(key_id: str) -> str:
    key_id = str(key_id).strip()
    if not KEY_ID_RE.fullmatch(key_id):
        raise ProvenanceError("key_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return key_id


def require_initialized_registry(root: str | Path) -> None:
    events = load_events(root)
    if not events or events[0].get("event_type") != "REGISTRY_INITIALIZED":
        raise ProvenanceError("provenance registry is not initialized")
    if any(e.get("event_type") == "REGISTRY_INITIALIZED" for e in events[1:]):
        raise ProvenanceError("multiple registry initialization events are forbidden")


def register_public_key(
    root: str | Path,
    *,
    key_id: str,
    public_key: Path,
    actor: str = "release-engineering",
    algorithm: str = "openssl-dgst-sha256",
    valid_days: int = 180,
    rotation_warning_days: int = 30,
    not_before: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    require_initialized_registry(root)
    key_id = _validate_key_id(key_id)
    events = load_events(root)
    trust = replay_trust_state(events)
    if key_id in trust:
        raise ProvenanceError("key_id already exists; use a new key_id for rotation")
    if int(rotation_warning_days) < 1:
        raise ProvenanceError("rotation_warning_days must be positive")
    now = datetime.now(timezone.utc)
    nbf = parse_utc(not_before) if not_before else now
    exp = parse_utc(expires_at) if expires_at else parse_utc(iso_after_days(int(valid_days), base=nbf))
    if exp is None or nbf is None or exp <= nbf:
        raise ProvenanceError("key expires_at must be after not_before")
    data = public_key.read_bytes()
    if b"PRIVATE KEY" in data:
        raise ProvenanceError("private key material must never enter the provenance registry")
    if b"PUBLIC KEY" not in data:
        raise ProvenanceError("expected PEM public key")
    obj = store_object(root, data)
    return append_event(
        root,
        event_type="KEY_REGISTERED",
        actor=actor,
        payload={
            "key_id": key_id,
            "algorithm": algorithm,
            "public_key_sha256": obj["sha256"],
            "public_key_object_sha256": obj["sha256"],
            "not_before": nbf.isoformat().replace("+00:00", "Z"),
            "expires_at": exp.isoformat().replace("+00:00", "Z"),
            "rotation_warning_days": int(rotation_warning_days),
        },
        objects=[{"kind": "public_key", **obj}],
    )


def revoke_public_key(root: str | Path, *, key_id: str, reason: str, actor: str = "release-engineering") -> dict[str, Any]:
    require_initialized_registry(root)
    key_id = _validate_key_id(key_id)
    trust = replay_trust_state(load_events(root))
    state = trust.get(key_id)
    if not state or state.get("status") != "ACTIVE":
        raise ProvenanceError("only an active registered key can be revoked")
    if not str(reason).strip():
        raise ProvenanceError("revocation reason is required")
    return append_event(root, event_type="KEY_REVOKED", actor=actor, payload={"key_id": key_id, "reason": str(reason)[:500]})


def verify_detached_signature(payload: bytes, signature: bytes, public_key: bytes) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="mgc-prov-verify-") as td:
        p = Path(td)
        payload_p, sig_p, key_p = p / "payload", p / "sig", p / "key.pem"
        payload_p.write_bytes(payload); sig_p.write_bytes(signature); key_p.write_bytes(public_key)
        proc = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(key_p), "-signature", str(sig_p), str(payload_p)], capture_output=True, text=True)
        return proc.returncode == 0, (proc.stdout or proc.stderr or "").strip()[:200]


def _active_key_material(root: str | Path, key_id: str, *, at: datetime | None = None) -> tuple[dict[str, Any], bytes]:
    trust = replay_trust_state(load_events(root))
    state = trust.get(_validate_key_id(key_id))
    if not state:
        raise ProvenanceError("unknown signing key_id")
    if state.get("status") != "ACTIVE":
        raise ProvenanceError("signing key is revoked")
    moment = at or datetime.now(timezone.utc)
    not_before = parse_utc(state.get("not_before"))
    expires_at = parse_utc(state.get("expires_at"))
    if not_before is not None and moment < not_before:
        raise ProvenanceError("signing key is not active yet")
    if expires_at is not None and moment >= expires_at:
        raise ProvenanceError("signing key is expired")
    return state, read_object(root, str(state["public_key_object_sha256"]))


def _artifact_contract(kind: str, doc: dict[str, Any]) -> tuple[str, bytes, tuple[bool | None, str | None, str]]:
    kind = kind.lower().strip()
    if kind == "acceptance":
        if doc.get("schema") != RELEASE_ACCEPTANCE_SCHEMA:
            raise ProvenanceError("acceptance schema mismatch")
        return "ACCEPTANCE_REGISTERED", acceptance_canonical_bytes(doc), validate_acceptance_integrity(doc)
    if kind == "baseline":
        if doc.get("schema") != APPROVED_BASELINE_SCHEMA:
            raise ProvenanceError("baseline schema mismatch")
        return "BASELINE_REGISTERED", acceptance_canonical_bytes(doc), validate_acceptance_integrity(doc)
    if kind == "load":
        if doc.get("schema") != LOAD_EVIDENCE_SCHEMA:
            raise ProvenanceError("load evidence schema mismatch")
        return "LOAD_EVIDENCE_REGISTERED", load_canonical_bytes(doc), validate_load_integrity(doc)
    if kind == "failover":
        return "FAILOVER_EVIDENCE_REGISTERED", json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"), (None, None, "")
    raise ProvenanceError("artifact kind must be acceptance, baseline, load, or failover")


def register_signed_artifact(root: str | Path, *, kind: str, document_path: Path, signature_path: Path | None, key_id: str | None, actor: str = "release-engineering") -> dict[str, Any]:
    require_initialized_registry(root)
    try:
        raw = document_path.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"invalid evidence document: {document_path.name}") from exc
    event_type, canonical, integrity = _artifact_contract(kind, doc)
    valid_digest, _claimed, actual_canonical = integrity
    if kind != "failover" and valid_digest is not True:
        raise ProvenanceError("evidence canonical digest invalid")

    objects: list[dict[str, Any]] = []
    doc_obj = store_object(root, raw)
    objects.append({"kind": f"{kind}_document", **doc_obj})
    signature_verified = False
    signer_key_id = None
    signature_obj = None
    if signature_path is not None or key_id is not None:
        if signature_path is None or key_id is None:
            raise ProvenanceError("signature_path and key_id must be provided together")
        _state, key_bytes = _active_key_material(root, key_id)
        sig_bytes = signature_path.read_bytes()
        ok, detail = verify_detached_signature(canonical, sig_bytes, key_bytes)
        if not ok:
            raise ProvenanceError(f"detached signature verification failed: {detail}")
        signature_verified = True; signer_key_id = key_id
        signature_obj = store_object(root, sig_bytes)
        objects.append({"kind": f"{kind}_signature", **signature_obj})
    elif kind in {"acceptance", "baseline", "load"}:
        raise ProvenanceError(f"{kind} registration requires a detached signature and active key_id")

    payload: dict[str, Any] = {
        "kind": kind,
        "release": doc.get("release"),
        "schema_version": doc.get("schema_version"),
        "profile": doc.get("profile"),
        "document_object_sha256": doc_obj["sha256"],
        "canonical_sha256": actual_canonical if kind != "failover" else sha256_bytes(canonical),
        "signature_verified": signature_verified,
        "signer_key_id": signer_key_id,
        "signature_object_sha256": signature_obj["sha256"] if signature_obj else None,
    }
    if kind == "acceptance":
        payload.update({
            "decision": doc.get("decision"),
            "technical_decision": doc.get("technical_decision"),
            "production_authorized": bool(doc.get("production_authorized")),
            "metrics": copy.deepcopy(doc.get("metrics") or {}),
            "chain": copy.deepcopy(doc.get("chain") or {}),
            "baseline_release": ((doc.get("baseline_regression") or {}).get("baseline_release")),
            "failed_checks": list(doc.get("failed_checks") or []),
        })
    elif kind == "baseline":
        payload.update({
            "technical_decision": doc.get("technical_decision"),
            "human_approved": bool(doc.get("human_approved")),
            "bootstrap": bool(doc.get("bootstrap")),
            "approval_reference": ((doc.get("approval") or {}).get("reference")),
            "source_acceptance_sha256": doc.get("source_acceptance_sha256"),
            "metrics": copy.deepcopy(doc.get("metrics") or {}),
        })
    elif kind == "load":
        payload.update({"summary": copy.deepcopy(doc.get("summary") or {}), "saturation": copy.deepcopy(doc.get("saturation") or {})})
    else:
        payload.update({"evidence_schema": doc.get("schema"), "failover": copy.deepcopy(doc.get("failover") or {})})
    return append_event(root, event_type=event_type, actor=actor, payload=payload, objects=objects)


def verify_registry(root: str | Path) -> dict[str, Any]:
    structural = verify_event_chain(root, verify_objects=True)
    if structural["status"] != "PASS":
        return {**structural, "crypto_status": "NOT_RUN"}
    events = load_events(root)
    if not events:
        return {**structural, "status": "FAIL", "crypto_status": "FAIL", "verified_signed_artifacts": 0, "crypto_failures": [{"sequence": None, "reason": "registry_uninitialized"}]}
    keys: dict[str, dict[str, Any]] = {}
    crypto_failures: list[dict[str, Any]] = []
    if events[0].get("event_type") != "REGISTRY_INITIALIZED":
        crypto_failures.append({"sequence": events[0].get("sequence"), "reason": "registry_first_event_not_initialized"})
    if any(e.get("event_type") == "REGISTRY_INITIALIZED" for e in events[1:]):
        crypto_failures.append({"sequence": None, "reason": "multiple_registry_initialization_events"})
    verified_signed_artifacts = 0
    for e in events:
        et = e.get("event_type")
        p = e.get("payload") or {}
        seq = e.get("sequence")
        if et == "KEY_REGISTERED":
            key_id = str(p.get("key_id") or "")
            if not KEY_ID_RE.fullmatch(key_id) or key_id in keys:
                crypto_failures.append({"sequence": seq, "reason": "invalid_or_duplicate_key_registration", "key_id": key_id})
                continue
            try:
                key_bytes = read_object(root, str(p.get("public_key_object_sha256") or ""))
            except ProvenanceError:
                crypto_failures.append({"sequence": seq, "reason": "missing_key_object", "key_id": key_id}); continue
            if b"PRIVATE KEY" in key_bytes or b"PUBLIC KEY" not in key_bytes:
                crypto_failures.append({"sequence": seq, "reason": "invalid_public_key_object", "key_id": key_id}); continue
            try:
                not_before = parse_utc(p.get("not_before"))
                expires_at = parse_utc(p.get("expires_at"))
                if not_before is not None and expires_at is not None and expires_at <= not_before:
                    raise ProvenanceError("invalid key validity window")
            except ProvenanceError:
                crypto_failures.append({"sequence": seq, "reason": "invalid_key_validity", "key_id": key_id}); continue
            keys[key_id] = {
                "status": "ACTIVE",
                "public_key": key_bytes,
                "not_before": not_before,
                "expires_at": expires_at,
            }
        elif et == "KEY_REVOKED":
            key_id = str(p.get("key_id") or "")
            if key_id not in keys or keys[key_id].get("status") != "ACTIVE":
                crypto_failures.append({"sequence": seq, "reason": "invalid_key_revocation", "key_id": key_id})
            else:
                keys[key_id]["status"] = "REVOKED"
        elif et in {"ACCEPTANCE_REGISTERED", "BASELINE_REGISTERED", "LOAD_EVIDENCE_REGISTERED"}:
            key_id = str(p.get("signer_key_id") or "")
            state = keys.get(key_id)
            if not state or state.get("status") != "ACTIVE":
                crypto_failures.append({"sequence": seq, "reason": "signer_not_active_at_registration", "key_id": key_id}); continue
            try:
                event_time = parse_utc(e.get("recorded_at"))
                if event_time is None:
                    raise ProvenanceError("missing event timestamp")
                if state.get("not_before") is not None and event_time < state["not_before"]:
                    crypto_failures.append({"sequence": seq, "reason": "signer_before_validity", "key_id": key_id}); continue
                if state.get("expires_at") is not None and event_time >= state["expires_at"]:
                    crypto_failures.append({"sequence": seq, "reason": "signer_expired_at_registration", "key_id": key_id}); continue
                doc_bytes = read_object(root, str(p.get("document_object_sha256") or ""))
                sig_bytes = read_object(root, str(p.get("signature_object_sha256") or ""))
                doc = json.loads(doc_bytes.decode("utf-8"))
                if et == "LOAD_EVIDENCE_REGISTERED":
                    valid, _c, _a = validate_load_integrity(doc); canonical = load_canonical_bytes(doc)
                else:
                    valid, _c, _a = validate_acceptance_integrity(doc); canonical = acceptance_canonical_bytes(doc)
                if valid is not True:
                    crypto_failures.append({"sequence": seq, "reason": "artifact_digest"}); continue
                ok, _detail = verify_detached_signature(canonical, sig_bytes, state["public_key"])
                if not ok:
                    crypto_failures.append({"sequence": seq, "reason": "artifact_signature", "key_id": key_id}); continue
                verified_signed_artifacts += 1
            except (ProvenanceError, UnicodeDecodeError, json.JSONDecodeError):
                crypto_failures.append({"sequence": seq, "reason": "artifact_object"})
    return {
        **structural,
        "status": "PASS" if not crypto_failures else "FAIL",
        "crypto_status": "PASS" if not crypto_failures else "FAIL",
        "verified_signed_artifacts": verified_signed_artifacts,
        "crypto_failures": crypto_failures,
    }


def registry_summary(root: str | Path) -> dict[str, Any]:
    try:
        verification = verify_event_chain(root, verify_objects=True)
        events = load_events(root)
    except ProvenanceError as exc:
        return {"schema": PROVENANCE_REGISTRY_SCHEMA, "status": "FAIL", "reason": str(exc), "production_authorized": False}
    if not events:
        return {"schema": PROVENANCE_REGISTRY_SCHEMA, "status": "UNINITIALIZED", "tip_sequence": 0, "tip_sha256": None, "event_counts": {}, "release_count": 0, "active_key_ids": [], "revoked_key_ids": [], "production_authorized": False}
    trust = replay_trust_state(events)
    counts: dict[str, int] = {}
    releases: set[str] = set()
    for e in events:
        et = str(e.get("event_type") or "UNKNOWN")
        counts[et] = counts.get(et, 0) + 1
        rel = ((e.get("payload") or {}).get("release"))
        if rel:
            releases.add(str(rel))
    return {
        "schema": PROVENANCE_REGISTRY_SCHEMA,
        "status": verification["status"],
        "tip_sequence": verification["tip_sequence"],
        "tip_sha256": verification["tip_sha256"],
        "event_counts": counts,
        "release_count": len(releases),
        "active_key_ids": sorted(k for k, v in trust.items() if v.get("status") == "ACTIVE"),
        "revoked_key_ids": sorted(k for k, v in trust.items() if v.get("status") == "REVOKED"),
        "production_authorized": False,
    }


def _acceptance_events(root: str | Path, *, profile: str | None = None) -> list[dict[str, Any]]:
    out = []
    for e in load_events(root):
        if e.get("event_type") != "ACCEPTANCE_REGISTERED":
            continue
        p = e.get("payload") or {}
        if profile is not None and str(p.get("profile")) != str(profile):
            continue
        out.append(e)
    return out


def compare_releases(root: str | Path, *, release_a: str, release_b: str, profile: str) -> dict[str, Any]:
    rows = _acceptance_events(root, profile=profile)
    by_release: dict[str, dict[str, Any]] = {}
    for e in rows:
        p = e.get("payload") or {}
        by_release[str(p.get("release"))] = p
    if release_a not in by_release or release_b not in by_release:
        raise ProvenanceError("both releases must have registered acceptance evidence for this profile")
    a, b = by_release[release_a], by_release[release_b]
    ma, mb = a.get("metrics") or {}, b.get("metrics") or {}
    metric_names = ["p95_ms", "p99_ms", "error_rate", "requests_per_second", "db_pool_max_saturation_ratio", "rto_seconds", "rpo_seconds"]
    deltas = {}
    for name in metric_names:
        av, bv = ma.get(name), mb.get(name)
        try:
            af, bf = float(av), float(bv)
            deltas[name] = {"a": af, "b": bf, "absolute_delta": bf - af, "ratio_b_over_a": None if af == 0 else bf / af}
        except (TypeError, ValueError):
            deltas[name] = {"a": av, "b": bv, "absolute_delta": None, "ratio_b_over_a": None}
    return {"schema": "mgc-release-regression-comparison-v1", "profile": str(profile), "release_a": release_a, "release_b": release_b, "metrics": deltas}


def build_audit_report(root: str | Path) -> dict[str, Any]:
    verification = verify_registry(root)
    events = load_events(root)
    trust = replay_trust_state(events)
    releases: dict[str, dict[str, Any]] = {}
    for e in events:
        p = e.get("payload") or {}
        release = p.get("release")
        if not release:
            continue
        row = releases.setdefault(str(release), {"release": str(release), "acceptance": [], "baselines": [], "load_evidence": 0, "failover_evidence": 0})
        et = e.get("event_type")
        if et == "ACCEPTANCE_REGISTERED":
            row["acceptance"].append({"sequence": e.get("sequence"), "profile": p.get("profile"), "decision": p.get("decision"), "technical_decision": p.get("technical_decision"), "canonical_sha256": p.get("canonical_sha256"), "signer_key_id": p.get("signer_key_id")})
        elif et == "BASELINE_REGISTERED":
            row["baselines"].append({"sequence": e.get("sequence"), "profile": p.get("profile"), "human_approved": p.get("human_approved"), "approval_reference": p.get("approval_reference"), "canonical_sha256": p.get("canonical_sha256"), "signer_key_id": p.get("signer_key_id")})
        elif et == "LOAD_EVIDENCE_REGISTERED": row["load_evidence"] += 1
        elif et == "FAILOVER_EVIDENCE_REGISTERED": row["failover_evidence"] += 1
    return {
        "schema": PROVENANCE_AUDIT_SCHEMA,
        "generated_at": utcnow_iso(),
        "registry_verification": verification,
        "trust_keys": sorted(trust.values(), key=lambda x: x["key_id"]),
        "releases": [releases[k] for k in sorted(releases, key=lambda x: tuple(int(v) for v in x.split(".")) if re.fullmatch(r"\d+\.\d+\.\d+", x) else (9999, 9999, 9999))],
        "production_authorized": False,
    }
