# v6.0.17 — Company Pilot Candidate

## Base pilot

- Added approved corporate pilot home UI for Chinese and English tracks.
- Chinese home uses Russian UI and Chinese daily phrase with Pinyin/translation.
- English home uses Russian UI, English hero copy and English daily phrase.
- Added deterministic daily phrase rotation and automatic midnight refresh.
- Added seven local/offline rotating production illustrations and two local hero artworks.
- Simplified pilot sidebar: no left notifications item; Chinese reference appears only for Chinese.
- Added secure company-pilot environment template.
- Added executable company pilot GO/NO-GO preflight.
- Added company pilot runbook, UAT checklist, participant template and feedback register.
- Added dedicated v6.0.17 CI contract.

## UX hardening — 08.09.2026

- Removed decorative quote/slogan blocks and extra hero messages from the rendered pilot UI.
- Added a Pinyin fallback layer for core Chinese automotive terms, including `整车装配 → zhěng chē zhuāng pèi`.
- Improved browser TTS voice selection: Natural/Neural/Online/Premium voices and suitable Mandarin/English voices are preferred; robotic fallback voices are deprioritized.
- Limited game generation to a maximum of **5 answers per game session** at backend level to reduce XP farming.
- Added local/offline thematic SVG artwork for assembly, welding, paint, stamping, quality and logistics topic cards.
- Removed unnecessary decorative hero artwork elements in both Chinese and English variants.
- Added release-specific `pilot_ux_hardening.js` and `pilot_overrides.css` layers.
- Added `tests/v617_pilot_ux_regression_test.py` and wired it into both active GitHub Actions workflows.
- Expanded CI syntax/artwork checks to cover the new UX hardening layer and topic artwork.
- Updated README and build information to match the current `main` pilot.

## Compatibility / backend note

ORM schema and Alembic head remain unchanged. The general XP award/anti-farm mechanism remains unchanged; only the number of generated answers in a game session is now capped at five.
