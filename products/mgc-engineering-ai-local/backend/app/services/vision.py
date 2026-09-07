import base64
import mimetypes
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.local_ai import validate_inference_url
from app.core.resilience import circuit_allows, record_failure, record_success


async def describe_image(path: Path) -> str | None:
    cfg = get_settings()
    if not cfg.vlm_base_url or not cfg.vlm_model or not circuit_allows("vlm"):
        return None
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    payload = {
        "model": cfg.vlm_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract engineering information visible in this image. Transcribe identifiers, dimensions, notes and tables. Do not infer values that are not legible."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
            ],
        }],
        "temperature": 0.0,
    }
    headers = {"Authorization": f"Bearer {cfg.vlm_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=cfg.vlm_timeout_seconds) as client:
            r = await client.post(validate_inference_url(cfg.vlm_base_url).rstrip("/") + "/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        record_failure("vlm", exc)
        return None
    record_success("vlm")
    return content
