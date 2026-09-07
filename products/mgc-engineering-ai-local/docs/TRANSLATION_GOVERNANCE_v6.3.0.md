# Engineering Translation Governance — v6.3.0

## BOM translation

BOM translation is an on-demand **view**, not a BOM mutation. The engineer can request Russian, English or Chinese display text. Part numbers, codes, dimensions, units, standards and numeric values are protected tokens and must survive translation unchanged.

An exact automotive glossary provides deterministic fallback for common terms. Broader translation may use only the configured approved local OpenAI-compatible model/gateway. If local AI is unavailable, the system does not silently send engineering text to an external web translator.

## Translation Memory

`EngineeringTranslationMemory` stores source hash, project/area scope, source and target languages, translated text, model/provider, warnings and review status. Reuse is exact-source-hash based; rejected entries are not reused.

## Work instructions

A Chinese/English partner WI keeps the original text/file. Russian content is stored separately with `pending/draft/reviewed/rejected` state. Translation does not introduce engineering facts. Human review is mandatory before a foreign WI can reach approved operational status.
