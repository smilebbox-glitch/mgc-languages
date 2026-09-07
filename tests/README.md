# Automated verification

This directory contains repository-level checks that complement the existing release regression shards, including v5.7.2 architecture/content guards.

## Test layers

1. **Content contracts** — `python tests/content_contract.py`
   - verifies all tracked source-language JSON files parse correctly;
   - checks Chinese foundations keep the Putonghua learning standard, five tones and reference groups;
   - checks automotive topics/roleplays have stable IDs and bilingual Chinese/English learning fields;
   - guards against accidentally dropping the large Chinese and English source corpora;
   - verifies the static UI assets required by the runtime are present;
   - verifies the FastAPI runtime actually ingests the tracked dictionaries.

2. **Existing regression suite** — `python scripts/run_release_tests.py --shard <name>`
   - base;
   - pronunciation;
   - putonghua;
   - reliability;
   - ops;
   - v57;
   - v571;
   - v572.

3. **Docker/runtime smoke** — `python tests/runtime_smoke.py`
   - public liveness contract;
   - readiness contract;
   - `/api/meta` and Putonghua learning-standard metadata;
   - HTML application shell;
   - production JavaScript and CSS assets.

A green CI workflow means the checked source compiles, source language content passes structural/runtime contracts, all release regression shards pass, the Docker image builds with offline TTS, the application starts, and the public runtime contract is reachable. It does not replace production acceptance, security review, or human linguistic/editorial approval.
