from __future__ import annotations

import hashlib
import re
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EngineeringTranslationMemory, BOMItem
from app.adapters.registry import get_translation_provider_port
from app.ports.translation import TranslationProviderPort

LANGUAGE_NAMES = {"ru": "Russian", "en": "English", "zh": "Simplified Chinese"}

# Conservative exact-term fallback for the most common BOM labels. Partial/creative
# machine translation is deliberately not attempted when local AI is unavailable.
EXACT_GLOSSARY = {
    "bolt": {"ru": "болт", "zh": "螺栓"},
    "nut": {"ru": "гайка", "zh": "螺母"},
    "washer": {"ru": "шайба", "zh": "垫圈"},
    "bracket": {"ru": "кронштейн", "zh": "支架"},
    "bumper": {"ru": "бампер", "zh": "保险杠"},
    "wiring harness": {"ru": "жгут проводов", "zh": "线束"},
    "connector": {"ru": "разъём", "zh": "连接器"},
    "seal": {"ru": "уплотнение", "zh": "密封件"},
    "gasket": {"ru": "прокладка", "zh": "垫片"},
    "bearing": {"ru": "подшипник", "zh": "轴承"},
    "sensor": {"ru": "датчик", "zh": "传感器"},
    "door": {"ru": "дверь", "zh": "车门"},
    "hood": {"ru": "капот", "zh": "发动机罩"},
    "fender": {"ru": "крыло", "zh": "翼子板"},
    "dashboard": {"ru": "панель приборов", "zh": "仪表板"},
    "seat": {"ru": "сиденье", "zh": "座椅"},
    "wheel": {"ru": "колесо", "zh": "车轮"},
    "wheel hub": {"ru": "ступица колеса", "zh": "轮毂"},
    "control arm": {"ru": "рычаг подвески", "zh": "控制臂"},
    "shock absorber": {"ru": "амортизатор", "zh": "减振器"},
    "螺栓": {"ru": "болт", "en": "bolt"},
    "螺母": {"ru": "гайка", "en": "nut"},
    "垫圈": {"ru": "шайба", "en": "washer"},
    "支架": {"ru": "кронштейн", "en": "bracket"},
    "保险杠": {"ru": "бампер", "en": "bumper"},
    "线束": {"ru": "жгут проводов", "en": "wiring harness"},
    "连接器": {"ru": "разъём", "en": "connector"},
    "密封件": {"ru": "уплотнение", "en": "seal"},
    "垫片": {"ru": "прокладка", "en": "gasket"},
    "轴承": {"ru": "подшипник", "en": "bearing"},
    "传感器": {"ru": "датчик", "en": "sensor"},
    "车门": {"ru": "дверь", "en": "door"},
    "座椅": {"ru": "сиденье", "en": "seat"},
    "车轮": {"ru": "колесо", "en": "wheel"},
}


def detect_language(text: str) -> str:
    value = text or ""
    if re.search(r"[\u4e00-\u9fff]", value):
        return "zh"
    if re.search(r"[А-Яа-яЁё]", value):
        return "ru"
    if re.search(r"[A-Za-z]", value):
        return "en"
    return "auto"


def source_hash(text: str) -> str:
    return hashlib.sha256(" ".join((text or "").split()).encode("utf-8")).hexdigest()


def protected_tokens(text: str) -> list[str]:
    """Tokens that a translation must preserve verbatim.

    We protect engineering identifiers, dimensions and numeric values. This is intentionally
    conservative: if the model changes one of these tokens the translation remains a draft
    with a warning rather than being silently trusted.
    """
    patterns = [
        r"\b[A-ZА-Я]{1,8}[-_/][A-ZА-Я0-9._/-]{1,32}\b",
        r"\b[A-Z]{2,}[0-9][A-Z0-9._/-]*\b",
        r"\b\d+(?:[.,]\d+)?\s?(?:mm|cm|m|kg|g|Nm|N·m|V|A|bar|MPa|kPa|°C|%)\b",
        r"\b\d+(?:[.,]\d+)?\b",
    ]
    out: list[str] = []
    for pattern in patterns:
        for token in re.findall(pattern, text or "", flags=re.IGNORECASE):
            if token not in out:
                out.append(token)
    return out


def validate_protected_tokens(source: str, translated: str) -> list[str]:
    return [token for token in protected_tokens(source) if token not in (translated or "")]


def _glossary_translation(text: str, target_language: str) -> str | None:
    key = " ".join((text or "").strip().lower().split())
    entry = EXACT_GLOSSARY.get(key)
    return entry.get(target_language) if entry else None


def _cached(db: Session, project_code: str | None, scope: str, text: str, target_language: str) -> EngineeringTranslationMemory | None:
    return db.scalar(select(EngineeringTranslationMemory).where(
        EngineeringTranslationMemory.project_code == project_code,
        EngineeringTranslationMemory.scope == scope,
        EngineeringTranslationMemory.source_hash == source_hash(text),
        EngineeringTranslationMemory.target_language == target_language,
        EngineeringTranslationMemory.status != "rejected",
    ).order_by(EngineeringTranslationMemory.updated_at.desc()))


async def _provider_translate(
    items: list[dict],
    target_language: str,
    translation_port: TranslationProviderPort | None = None,
) -> tuple[dict[str, str], str | None, str]:
    """Translate through a technology-neutral provider port.

    Translation memory, engineering token validation and human review remain in
    this application service. Concrete HTTP/model details live in adapters.
    """
    provider = translation_port or get_translation_provider_port()
    batch = await provider.translate_items(items, target_language)
    return batch.translations, batch.model, batch.provider


async def translate_texts(
    db: Session,
    texts: Iterable[str],
    *,
    project_code: str | None,
    manufacturing_area: str | None,
    scope: str,
    target_language: str,
    source_language: str = "auto",
    user: str = "system",
    force: bool = False,
    translation_port: TranslationProviderPort | None = None,
) -> list[dict]:
    values = list(texts)
    results: list[dict | None] = [None] * len(values)
    pending: list[tuple[int, str, str]] = []
    for idx, text in enumerate(values):
        clean = (text or "").strip()
        detected = detect_language(clean) if source_language == "auto" else source_language
        if not clean:
            results[idx] = {"source": text, "translation": "", "source_language": detected, "target_language": target_language, "status": "empty", "warnings": []}
            continue
        if detected == target_language:
            results[idx] = {"source": text, "translation": clean, "source_language": detected, "target_language": target_language, "status": "not_required", "warnings": []}
            continue
        if not force:
            cached = _cached(db, project_code, scope, clean, target_language)
            if cached:
                results[idx] = {
                    "translation_id": cached.id, "source": clean, "translation": cached.translated_text,
                    "source_language": cached.source_language, "target_language": cached.target_language,
                    "status": cached.status, "warnings": cached.warnings_json or [], "cached": True,
                }
                continue
        exact = _glossary_translation(clean, target_language)
        if exact:
            pending_id = f"g{idx}"
            results[idx] = {"source": clean, "translation": exact, "source_language": detected, "target_language": target_language, "status": "draft", "warnings": [], "provider": "approved_glossary"}
            pending.append((idx, pending_id, "__GLOSSARY__"))
        else:
            pending.append((idx, str(idx), clean))

    llm_pending = [{"id": pid, "source_language": detect_language(text) if source_language == "auto" else source_language, "text": text}
                   for _, pid, text in pending if text != "__GLOSSARY__"]
    translated_map: dict[str, str] = {}
    model: str | None = None
    provider_name: str | None = None
    if llm_pending:
        try:
            translated_map, model, provider_name = await _provider_translate(llm_pending, target_language, translation_port)
        except Exception as exc:
            translated_map = {}
            model = None
            llm_error = type(exc).__name__
        else:
            llm_error = None
    else:
        llm_error = None

    for idx, pid, text in pending:
        if text == "__GLOSSARY__":
            base = results[idx] or {}
            translated = str(base.get("translation") or "")
            detected = str(base.get("source_language") or source_language)
            provider_model = "approved_glossary"
            warnings: list[str] = []
        else:
            source = values[idx].strip()
            detected = detect_language(source) if source_language == "auto" else source_language
            translated = translated_map.get(pid, "")
            provider_model = model or provider_name
            if not translated:
                warnings = ["local_ai_translation_unavailable" + (f":{llm_error}" if llm_error else "")]
                results[idx] = {"source": source, "translation": None, "source_language": detected, "target_language": target_language, "status": "unavailable", "warnings": warnings}
                continue
            missing = validate_protected_tokens(source, translated)
            warnings = [f"protected_token_missing:{token}" for token in missing]
        source = values[idx].strip()
        existing = _cached(db, project_code, scope, source, target_language)
        if existing:
            row = existing
            row.translated_text = translated
            row.source_language = detected
            row.status = "draft"
            row.model = provider_model
            row.warnings_json = warnings
            row.created_by = user
        else:
            row = EngineeringTranslationMemory(
                project_code=project_code, manufacturing_area=manufacturing_area, scope=scope,
                source_hash=source_hash(source), source_language=detected, target_language=target_language,
                source_text=source, translated_text=translated, status="draft", model=provider_model,
                warnings_json=warnings, created_by=user,
            )
            db.add(row)
        db.flush()
        results[idx] = {
            "translation_id": row.id, "source": source, "translation": translated,
            "source_language": detected, "target_language": target_language,
            "status": "draft", "warnings": warnings, "cached": False,
            "provider": provider_model or "local_ai",
        }
    db.commit()
    return [x or {"source": values[i], "translation": None, "status": "unavailable", "warnings": ["translation_error"]} for i, x in enumerate(results)]


async def translate_bom(
    db: Session,
    rows: list[BOMItem],
    *,
    project_code: str | None,
    manufacturing_area: str | None,
    target_language: str,
    source_language: str,
    user: str,
    refresh: bool = False,
) -> dict:
    texts = [x.description or "" for x in rows]
    translations = await translate_texts(
        db, texts, project_code=project_code, manufacturing_area=manufacturing_area, scope="bom_description",
        target_language=target_language, source_language=source_language, user=user, force=refresh,
    )
    items = []
    for row, tr in zip(rows, translations):
        items.append({
            "child_part_number": row.child_part_number,
            "child_revision": row.child_revision,
            "quantity": row.quantity,
            "unit": row.unit,
            "position": row.position,
            "supplier_code": row.supplier_code,
            "supplier_name": row.supplier_name,
            "source_document_id": row.source_document_id,
            "description_original": row.description,
            "description_translated": tr.get("translation"),
            "translation_status": tr.get("status"),
            "translation_warnings": tr.get("warnings") or [],
            "translation_id": tr.get("translation_id"),
            "source_language": tr.get("source_language"),
            "target_language": target_language,
        })
    return {
        "target_language": target_language,
        "source_is_immutable": True,
        "human_review_recommended": True,
        "items": items,
        "translated_count": sum(bool(x.get("description_translated")) for x in items),
        "unavailable_count": sum(x.get("translation_status") == "unavailable" for x in items),
    }
