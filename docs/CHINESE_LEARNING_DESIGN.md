# Chinese Learning Design — beginner-first v5.2.2

## Objective
A Russian-speaking employee with zero Chinese should understand the basic sound system before technical vocabulary becomes intimidating. The module uses short visual chunks, automotive examples and repeatable audio rather than linguistic terminology for its own sake.

## Core mental model
Chinese characters are not an alphabet. **Pinyin** is a Latin-script pronunciation notation.

A practical Pinyin syllable is taught as:

`initial + final + tone`

Example: `zh + i + 4th tone = zhì`.

The Russian “как читать” line is deliberately presented as approximate scaffolding, not as phonetic truth.

## Tones
Mandarin uses four lexical tones plus a neutral tone. Tone is part of a syllable's pronunciation and can distinguish words.

Simple movement metaphors:
- 1st: flat/high — “hold one note”.
- 2nd: rising — “as if asking?”.
- 3rd: low/dipping — “voice goes down; the full rise may shrink in connected speech”.
- 4th: sharp falling — “short confident command”.
- neutral: light/short.

## Context: what really happens in a conversation
The course does not teach the false idea that “Chinese people understand everything from context, so tones do not matter”. A listener combines:
1. pronunciation and tone;
2. neighboring words and common combinations;
3. grammar;
4. topic of the conversation;
5. workplace situation and visible objects;
6. the type of answer they expect.

Context can rescue imperfect learner speech. It cannot guarantee understanding. `mǎi` (buy) / `mài` (sell) is used because a tone error can reverse a business action.

## “Chinese alphabet” request
Learners often ask for a Chinese alphabet. The interface answers the intent without teaching a false concept:
- **initials** = common syllable beginnings;
- **finals** = main vowel/nasal portions;
- a real Hanzi example demonstrates each sound;
- ▶ plays the Hanzi syllable so TTS does not pronounce the Latin letter name.

The map includes `g/k/h` and the important Russian-speaker contrasts `j/q/x`, `zh/ch/sh/r`, `z/c/s`, plus `ü`.

## Progressive removal of scaffolding
Recommended beginner path:
1. hear tones and several sound examples;
2. repeat ten starter terms at normal/slow speed;
3. hide approximate Cyrillic reading while keeping Pinyin;
4. later hide Pinyin in exercises when Hanzi + sound become familiar.

This avoids forcing a beginner to jump directly from Russian to characters.

## What “good enough” means for the pilot
The first goal is **intelligibility**, not accent perfection. Users should learn stable contrasts that affect comprehension and say short workplace phrases clearly. The app explicitly encourages listening and repetition instead of over-trusting Cyrillic approximations.

## Production-quality audio boundary
The offline voice is a stability/privacy layer. It is intentionally replaceable by an approved corporate/neural Mandarin voice later, while retaining the same API and learning UI.

## v5.3 — Putonghua and regional varieties
The beginner module now explains **普通话 (Putonghua)** as the practical nationwide standard for cross-regional communication. It explicitly avoids the false simplification “China has exactly 10 dialects”. Instead it presents the Ministry of Education's ten **major groups** and explains that many local varieties exist inside them.

The learner sees:
- Putonghua vs everyday Beijing local speech;
- accent vs local variety;
- why regional colleagues may switch speech style among themselves;
- Sichuanese as a familiar example of Southwestern Mandarin;
- Cantonese/Yue and Shanghainese/Wu as examples of varieties that may be hard for a Putonghua-only learner to understand;
- the useful phrase `请说普通话，可以吗？`.

Regional varieties are framed as normal linguistic diversity, not mistakes. No dialect competence score is created.

## No voice recording
v5.3 remains **listen-only**. The browser is not permitted to access the microphone (`Permissions-Policy: microphone=()`). No audio capture, storage, speech-recognition transcript or pronunciation-scoring pipeline is included.
