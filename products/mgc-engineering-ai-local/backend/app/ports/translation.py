from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TranslationBatch:
    translations: dict[str, str]
    model: str | None
    provider: str


class TranslationProviderPort(Protocol):
    """Machine-translation provider contract.

    Translation memory, protected-token validation and human review stay in the
    application layer; the adapter only translates supplied text.
    """

    mode: str

    @property
    def available(self) -> bool: ...

    async def translate_items(self, items: list[dict], target_language: str) -> TranslationBatch: ...
