from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

EVIDENCE_SCHEMA = "mgc-evidence-ref-v1"

@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_type: str
    evidence_id: str
    source_system: str = "mgc"
    document_id: str | None = None
    revision: str | None = None
    locator: str | None = None
    confidence: float | None = None

    def public(self) -> dict[str, Any]:
        return {"schema": EVIDENCE_SCHEMA, **{k: v for k, v in asdict(self).items() if v is not None}}


def normalize_evidence(value: EvidenceRef | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, EvidenceRef):
        return value.public()
    raw = dict(value or {})
    return {
        "schema": EVIDENCE_SCHEMA,
        "evidence_type": str(raw.get("evidence_type") or raw.get("type") or "record"),
        "evidence_id": str(raw.get("evidence_id") or raw.get("id") or ""),
        **({"source_system": str(raw.get("source_system"))} if raw.get("source_system") else {}),
        **({"document_id": str(raw.get("document_id"))} if raw.get("document_id") else {}),
        **({"revision": str(raw.get("revision"))} if raw.get("revision") else {}),
        **({"locator": str(raw.get("locator"))} if raw.get("locator") else {}),
        **({"confidence": float(raw.get("confidence"))} if raw.get("confidence") is not None else {}),
    }


def evidence_bundle(values: Iterable[EvidenceRef | dict[str, Any]], *, require_document_visibility: set[str] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for value in values:
        row = normalize_evidence(value)
        doc_id = row.get("document_id")
        if require_document_visibility is not None and doc_id and doc_id not in require_document_visibility:
            # Fail closed: a derived result must never disclose a hidden evidence reference.
            return []
        key = (row["evidence_type"], row["evidence_id"], doc_id)
        if key not in seen:
            seen.add(key); out.append(row)
    return out
