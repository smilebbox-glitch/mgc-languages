> Historical acceptance notes for v5.2.x. For the current release use `docs/IT_ACCEPTANCE_v5.3.md`.

# MGC Languages v5.2 — IT Acceptance

## Release acceptance gates
1. `bash scripts/static_preflight.sh` passes.
2. Fresh database reaches Alembic head `c8f1a52e1a20`.
3. Pilot preflight has no blocking configuration errors.
4. Only edge proxy is host-published in pilot Compose.
5. `/health/live` and `/health/ready` return 200.
6. `/api/meta` reports v5.2.
7. `/api/pronunciation/status` reports server engine or explicit browser fallback.
8. Chinese and English audio endpoint returns a valid RIFF/WAV when server TTS is enabled.
9. User can toggle Pinyin and reading preferences and they persist.
10. Manager cannot read an employee from another department.
11. Admin can see pilot telemetry; Editor cannot see employee analytics.
12. OIDC claim/group configuration passes `scripts/oidc_config_check.py` before IdP acceptance.
13. Non-destructive load smoke completes with zero request failures at the agreed sandbox concurrency.
14. PostgreSQL backup is produced with SHA-256 and `restore_rehearsal.sh` restores it into a temporary DB successfully.
15. Real corporate IdP login/logout, role mapping and department mapping are documented with test users before controlled pilot sign-off.

## Suggested pilot evidence bundle
Keep the output of:
```bash
bash scripts/static_preflight.sh
python scripts/pilot_preflight.py
python scripts/oidc_config_check.py
python scripts/container_smoke.py
python scripts/it_acceptance_v52.py
python scripts/load_smoke.py --requests 500 --workers 20 --include-audio
bash scripts/backup_postgres.sh
bash scripts/restore_rehearsal.sh backups/<dump>
```
plus `docker compose ps`, application image digest and the final `.env.pilot` values with secrets redacted.

## Load-test boundary
`load_smoke.py` is deliberately a small acceptance smoke, not capacity certification. Production sizing requires an agreed workload model, target concurrent users, database resources, network/ingress topology and representative SSO behavior.

## v5.2.1 pronunciation addendum
16. `/api/pronunciation/status` reports successful `language_checks` for both Chinese and English before server TTS is considered available.
17. Chinese initial/final sound-map controls play Hanzi example syllables, not isolated Latin letter names.
18. Server audio returns `X-TTS-Engine`, `X-TTS-Voice` and private cache headers.
19. Frontend audio has bounded server wait time and browser fallback (`AbortController`).
20. Technical English acronym reading aid handles at least PPAP/CMM without showing raw unknown Latin text as the only beginner aid.


## v5.2.2 Tone Lab addendum
- Open 中文 → “Информация о китайском” and start Tone Lab.
- Verify five short rounds can play Chinese audio and accept one of four tone directions.
- Verify immediate feedback appears after each answer.
- Verify finishing the lab records one idempotent practice result; re-submission of the same session does not award XP twice.
