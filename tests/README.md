# Automated verification

This directory contains repository-level checks that complement the existing v5.7/v5.7.1/v5.7.2 regression shards.

## Test layers

1. **Content contracts** — `python tests/content_contract.py`
   - verifies all tracked source-language JSON files parse correctly;
   - checks Chinese foundations keep the Putonghua learning standard, five tones, Pinyin guidance and reference groups using the actual v5.7.1 release structure;
   - checks automotive topics/roleplays have stable IDs and bilingual Chinese/English learning fields;
   - guards against accidentally dropping the large Chinese and English source corpora;
   - verifies the real FastAPI runtime ingests both language dictionaries;
   - verifies the static UI assets required by the runtime are present.

2. **Existing regression suite** — `python scripts/run_release_tests.py --shard <name>`
   - base;
   - pronunciation;
   - putonghua;
   - reliability;
   - ops;
   - v57;
   - v571;
   - v572;
   - content (local convenience shard for the content contract).

3. **Docker/runtime smoke** — `python tests/runtime_smoke.py`
   - public health contract;
   - readiness contract;
   - `/api/meta` language/Putonghua contract;
   - HTML application shell;
   - production JavaScript and CSS assets.

A green CI workflow means the checked source compiles, source language content passes structural/semantic contracts, all existing release regression shards pass, the Docker image builds with offline TTS, the application starts and the public runtime contract is reachable. It does not replace production acceptance, security review or human language/content approval.
