# Changelog v5.3.2 — Schema Readiness / Pilot Policy Gates

## Pilot / IT hardening
- Added Alembic schema-head validation to `/health/ready`.
- Packaged migration head is `c8f1a52e1a20`; a stale or missing migration can no longer report healthy when `READY_REQUIRE_SCHEMA_HEAD=true`.
- Added configurable readiness policy gates for:
  - corporate OIDC requirement;
  - disabled self-registration;
  - protected metrics endpoint;
  - Secure cookies after TLS integration;
  - explicit Trusted Hosts and non-wildcard CORS.
- Added `EXPECTED_ALEMBIC_HEAD` to make the deployment contract visible to IT.
- Extended `.env.pilot.example` and `docker-compose.pilot.yml` with explicit readiness controls.
- Updated pilot preflight to validate the same policy before container launch.
- Fixed a false-positive preflight failure where built-in TTS voice defaults (`zh`, `en-us`) were successfully probed but then incorrectly treated as missing env values.

## Verification
- New `v532_schema_readiness_test.py` proves a deliberately stale Alembic version returns HTTP 503 from readiness.
- New `it_acceptance_v532.py` verifies live/ready, schema head, Admin login, Putonghua content, real POST WAV pronunciation, telemetry, system summary and protected metrics through a real HTTP process.
- Local concurrent load smoke with audio: 240/240 successful requests, 16 workers.

## No user-facing regression
- XP economy, 100 levels, spendable XP, nudges, Admin content management, Tone Lab, Pinyin controls, Putonghua/dialect module and playback-only pronunciation remain unchanged.
- No microphone capture or voice recording was introduced.
- Added `scripts/migrate_safe.py`: PostgreSQL advisory lock serializes Alembic startup migrations if multiple app instances start together.
