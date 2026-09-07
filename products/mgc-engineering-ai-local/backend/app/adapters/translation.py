from __future__ import annotations

import json
import re

from app.ports.translation import TranslationBatch


LANGUAGE_NAMES = {"ru": "Russian", "en": "English", "zh": "Simplified Chinese"}


class DisabledTranslationProviderAdapter:
    mode = "disabled"

    @property
    def available(self) -> bool:
        return False

    async def translate_items(self, items: list[dict], target_language: str) -> TranslationBatch:
        return TranslationBatch({}, None, self.mode)


class OpenAICompatibleTranslationAdapter:
    mode = "openai_compatible_local"

    @property
    def available(self) -> bool:
        from app.core.config import get_settings
        cfg = get_settings()
        from app.core.resilience import circuit_allows
        return bool("local_llm" in cfg.runtime_features and cfg.llm_base_url and cfg.llm_model and circuit_allows("local_ai"))

    async def translate_items(self, items: list[dict], target_language: str) -> TranslationBatch:
        import httpx
        from app.core.config import get_settings
        from app.services.local_ai import validate_inference_url

        cfg = get_settings()
        if not self.available:
            return TranslationBatch({}, None, self.mode)
        prompt = {
            "task": "Translate automotive engineering text without interpretation.",
            "target_language": LANGUAGE_NAMES[target_language],
            "rules": [
                "Preserve part numbers, codes, dimensions, units, values, standards and acronyms verbatim.",
                "Do not add technical requirements, torque values, PPE, warnings, approvals or explanations.",
                "Translate names/descriptions only; keep supplier legal names unchanged unless a standard Russian name is obvious.",
                "Return only valid JSON: {\"items\":[{\"id\":\"...\",\"translation\":\"...\"}]}",
            ],
            "items": items,
        }
        payload = {
            "model": cfg.llm_model,
            "messages": [
                {"role": "system", "content": "You are a controlled automotive translation engine. Do not infer missing engineering facts."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0,
            "max_tokens": min(max(cfg.llm_max_tokens, 1024), 8192),
        }
        from app.core.resilience import record_failure, record_success
        try:
            async with httpx.AsyncClient(timeout=cfg.llm_timeout_seconds) as client:
                response = await client.post(
                    validate_inference_url(cfg.llm_base_url).rstrip("/") + "/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {cfg.llm_api_key}"},
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            record_failure("local_ai", exc)
            raise
        record_success("local_ai")
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
        data = json.loads(content)
        rows = data.get("items", []) if isinstance(data, dict) else []
        translations = {str(x.get("id")): str(x.get("translation", "")) for x in rows if isinstance(x, dict) and x.get("id") is not None}
        return TranslationBatch(translations, cfg.llm_model, self.mode)
