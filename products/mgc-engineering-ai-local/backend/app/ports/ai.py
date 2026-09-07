from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AICompletion:
    content: str
    model: str | None
    provider: str


class AIAnalysisPort(Protocol):
    """Controlled text-generation contract used only after evidence retrieval."""

    mode: str

    @property
    def available(self) -> bool: ...

    async def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.05,
        max_tokens: int | None = None,
    ) -> AICompletion: ...
