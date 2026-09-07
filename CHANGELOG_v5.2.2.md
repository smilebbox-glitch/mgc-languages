# CHANGELOG — MGC Languages v5.2.2

## Tone Lab — beginner listening practice
- Added a lightweight 5-round **Tone Lab** inside “Китайский без страха”.
- User hears a real Chinese syllable and chooses the direction of the tone: level / rising / dipping / falling.
- Immediate feedback explains the tone with a simple voice-motion metaphor and re-shows Hanzi + Pinyin + meaning.
- Tone Lab is deliberately short (about two minutes) and is not treated as a high-stakes test.
- Results are recorded through the existing practice ledger and award a small amount of XP.
- Practice session IDs are idempotent: re-submitting the same Tone Lab session does not grant XP twice.

## Pilot safety / compatibility
- No database migration is required from v5.2/v5.2.1.
- Existing Chinese foundations, Pinyin visibility settings, Russian reading aid, server TTS/browser fallback, department RBAC and v5 gamification remain backward-compatible.
- Added `v522_tone_lab_test.py` to regression coverage.
