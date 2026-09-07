from __future__ import annotations

import hashlib
import hmac
import time


def verify_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    secret: str,
    max_skew_seconds: int = 300,
    now: int | None = None,
) -> bool:
    try:
        ts = int(timestamp)
    except Exception:
        return False
    current = int(time.time()) if now is None else int(now)
    if abs(current - ts) > max_skew_seconds:
        return False
    expected = hmac.new(secret.encode("utf-8"), timestamp.encode("utf-8") + b"." + body, hashlib.sha256).hexdigest()
    supplied = signature.removeprefix("sha256=").strip().lower()
    return hmac.compare_digest(expected, supplied)
