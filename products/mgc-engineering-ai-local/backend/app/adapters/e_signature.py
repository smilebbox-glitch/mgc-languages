from __future__ import annotations


class DisabledElectronicSignatureAdapter:
    def availability(self) -> dict:
        return {"configured": False, "qualified_electronic_signature": False, "mode": "disabled"}

    def sign_digest(self, digest_sha256: str, context: dict) -> dict:
        raise RuntimeError("Corporate electronic-signature adapter is not configured")
