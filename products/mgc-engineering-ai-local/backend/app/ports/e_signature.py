from __future__ import annotations
from typing import Protocol


class ElectronicSignaturePort(Protocol):
    """Boundary for a future corporate PKI/e-sign provider.

    Implementations must sign a precomputed digest/manifest identity. They must never
    silently convert MGC approval evidence into a legal/qualified signature claim.
    """
    def availability(self) -> dict: ...
    def sign_digest(self, digest_sha256: str, context: dict) -> dict: ...
