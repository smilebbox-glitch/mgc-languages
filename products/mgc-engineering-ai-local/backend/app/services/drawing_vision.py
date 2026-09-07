from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.local_ai import validate_inference_url
from app.core.resilience import circuit_allows, record_failure, record_success


PROMPT = """Inspect this engineering drawing page. Extract only information visibly supported by the image.
Return ONLY valid JSON with this shape:
{
  "title_block": {"part_number": null, "revision": null, "material": null, "scale": null},
  "entities": [
    {"type": "dimension|diameter|radius|thread|surface_finish|datum|gdt|note|standard",
     "raw": "visible text/symbol", "value": null, "unit": null,
     "upper_tolerance": null, "lower_tolerance": null,
     "bbox_2d": [x1,y1,x2,y2], "confidence": 0.0}
  ],
  "warnings": []
}
Coordinates bbox_2d must be normalized integers from 0 to 1000. If a value is unreadable, use null and add a warning.
Never infer hidden dimensions, material, tolerances, GD&T, defect causes, or approval status. This is AI-assisted transcription, not authoritative metrology."""


def _render_pdf(path: Path, max_pages: int) -> list[tuple[str, bytes, str]]:
    import fitz

    doc = fitz.open(str(path))
    out = []
    try:
        for idx in range(min(len(doc), max_pages)):
            page = doc[idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), alpha=False)
            out.append((f"page_{idx+1}", pix.tobytes("png"), "image/png"))
    finally:
        doc.close()
    return out


def _images(path: Path, max_pages: int) -> list[tuple[str, bytes, str]]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _render_pdf(path, max_pages)
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        return [(path.stem, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/png")]
    return []


def _json_from_response(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"entities": [], "warnings": ["VLM returned non-object JSON"], "raw": raw[:8000]}
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if 0 <= start < end:
            try:
                value = json.loads(raw[start:end+1])
                if isinstance(value, dict):
                    return value
            except Exception:
                pass
    return {"entities": [], "warnings": ["VLM response was not valid JSON"], "raw": raw[:8000]}


def _norm_value(item: dict) -> tuple:
    typ = str(item.get("type") or "").lower()
    raw = str(item.get("raw") or "").upper().replace(" ", "")
    value = item.get("nominal", item.get("value"))
    try:
        value = round(float(value), 4) if value is not None else None
    except Exception:
        value = str(value).upper() if value is not None else None
    return typ, value, raw[:80]


def build_consensus(deterministic_entities: list[dict], vlm_pages: list[dict]) -> dict:
    vlm_entities: list[dict] = []
    for page in vlm_pages:
        payload = page.get("structured") or {}
        for entity in payload.get("entities") or []:
            if isinstance(entity, dict):
                entity = dict(entity)
                entity.setdefault("page", page.get("page_number"))
                entity["source_method"] = "local_vlm"
                entity["authoritative"] = False
                vlm_entities.append(entity)

    confirmed: list[dict] = []
    disagreements: list[dict] = []
    unmatched_vlm: list[dict] = []
    used: set[int] = set()
    for det in deterministic_entities:
        dkey = _norm_value(det)
        candidates = []
        for idx, vlm in enumerate(vlm_entities):
            if idx in used:
                continue
            vkey = _norm_value(vlm)
            if dkey[0] and vkey[0] and dkey[0] != vkey[0]:
                continue
            score = 0
            if dkey[1] is not None and dkey[1] == vkey[1]:
                score += 3
            if dkey[2] and vkey[2] and (dkey[2] in vkey[2] or vkey[2] in dkey[2]):
                score += 2
            if det.get("page") and vlm.get("page") and det.get("page") == vlm.get("page"):
                score += 1
            if score:
                candidates.append((score, idx, vlm))
        if candidates:
            score, idx, vlm = max(candidates, key=lambda x: x[0])
            used.add(idx)
            if score >= 3:
                confirmed.append({"deterministic": det, "vlm": vlm, "consensus_confidence": min(0.999, max(float(det.get("confidence") or 0.0), float(vlm.get("confidence") or 0.0), 0.985))})
            else:
                disagreements.append({"deterministic": det, "vlm": vlm, "reason": "weak_match"})

    unmatched_vlm = [x for i, x in enumerate(vlm_entities) if i not in used]
    return {
        "deterministic_entity_count": len(deterministic_entities),
        "vlm_entity_count": len(vlm_entities),
        "confirmed": confirmed,
        "disagreements": disagreements,
        "unmatched_vlm": unmatched_vlm,
        "policy": "Deterministic/vector evidence remains authoritative; VLM can confirm or flag review candidates but cannot overwrite it.",
    }


async def inspect_drawing(path: Path, max_pages: int = 3, deterministic_analysis: dict | None = None) -> dict:
    cfg = get_settings()
    if not cfg.vlm_base_url or not cfg.vlm_model:
        return {"configured": False, "pages": [], "warning": "VLM_MODEL/VLM_BASE_URL not configured"}
    if not circuit_allows("vlm"):
        return {"configured": True, "pages": [], "warning": "VLM temporarily unavailable; deterministic drawing analysis remains available", "brownout": True}
    pages = _images(path, max(1, min(max_pages, 8)))
    if not pages:
        return {"configured": True, "pages": [], "warning": "Unsupported file type for visual inspection"}
    headers = {"Authorization": f"Bearer {cfg.vlm_api_key}"}
    results = []
    async with httpx.AsyncClient(timeout=cfg.vlm_timeout_seconds) as client:
        for idx, (label, raw, mime) in enumerate(pages, start=1):
            b64 = base64.b64encode(raw).decode()
            payload = {
                "model": cfg.vlm_model,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ]}],
                "temperature": 0.0,
                "max_tokens": 4096,
            }
            try:
                r = await client.post(validate_inference_url(cfg.vlm_base_url).rstrip("/") + "/chat/completions", json=payload, headers=headers)
                r.raise_for_status()
                raw_response = r.json()["choices"][0]["message"]["content"]
            except Exception as exc:
                record_failure("vlm", exc)
                return {"configured": True, "pages": results, "warning": "VLM request failed; deterministic drawing analysis remains available", "brownout": True}
            record_success("vlm")
            results.append({"page": label, "page_number": idx, "structured": _json_from_response(raw_response)})

    deterministic_entities = ((deterministic_analysis or {}).get("entities") or [])
    return {
        "configured": True,
        "pages": results,
        "ai_extracted": True,
        "authoritative": False,
        "consensus": build_consensus(deterministic_entities, results),
    }
