from __future__ import annotations

from app.ports.ai import AICompletion


class DisabledAIAnalysisAdapter:
    mode = "disabled"

    @property
    def available(self) -> bool:
        return False

    async def complete(self, messages: list[dict], *, temperature: float = 0.05, max_tokens: int | None = None) -> AICompletion:
        raise RuntimeError("AI analysis adapter is disabled for this runtime profile")


class OpenAICompatibleAIAdapter:
    mode = "openai_compatible_local"

    @property
    def available(self) -> bool:
        from app.core.config import get_settings
        cfg = get_settings()
        from app.core.resilience import circuit_allows
        return bool("local_llm" in cfg.runtime_features and cfg.llm_base_url and cfg.llm_model and circuit_allows("local_ai"))

    async def complete(self, messages: list[dict], *, temperature: float = 0.05, max_tokens: int | None = None) -> AICompletion:
        import httpx
        from app.core.config import get_settings
        from app.services.local_ai import validate_inference_url

        cfg = get_settings()
        if not self.available:
            raise RuntimeError("Local AI is unavailable")
        payload = {
            "model": cfg.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or cfg.llm_max_tokens,
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
                content = response.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            record_failure("local_ai", exc)
            raise
        record_success("local_ai")
        return AICompletion(content=str(content), model=cfg.llm_model, provider=self.mode)
