from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

@dataclass(slots=True)
class HandoverDeliveryResult:
    ok: bool
    status: str
    external_receipt_id: str | None = None
    response: dict[str, Any] = field(default_factory=dict)
    target_state_sha256: str | None = None

class HandoverWritePort(Protocol):
    def execute(self, *, system, target, payload: dict[str, Any], headers: dict[str, str]) -> HandoverDeliveryResult: ...
    def reconcile(self, *, system, target, external_receipt_id: str, headers: dict[str, str]) -> HandoverDeliveryResult: ...
