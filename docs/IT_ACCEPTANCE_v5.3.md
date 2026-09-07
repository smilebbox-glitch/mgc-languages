# MGC Languages v5.3 — IT Acceptance

## Automated release gates
1. `bash scripts/static_preflight.sh` passes the complete regression suite.
2. Fresh database reaches Alembic head `c8f1a52e1a20` (v5.3 adds no schema changes).
3. `python scripts/pilot_preflight.py` has no blocking configuration findings.
4. Pilot Compose publishes only Nginx; app and PostgreSQL remain internal.
5. App runs non-root/read-only with dropped Linux capabilities.
6. `/health/live` and `/health/ready` return 200.
7. `/api/meta` reports `5.3.0`, `voice_recording_enabled=false` and `pronunciation_transport=POST`.
8. Security headers include `Permissions-Policy: ... microphone=()`.
9. `/api/chinese/foundations` contains the Putonghua section and exactly 10 **major groups**, not a claim of exactly 10 local dialects.
10. Pinyin/reading preferences persist and Tone Lab remains idempotent for XP.

## Pronunciation / TTS acceptance
11. New frontend requests pronunciation with `POST /api/pronunciation/audio`; phrase text is not placed in the URL.
12. `/api/pronunciation/status` reports language probes, timeout, concurrency, circuit state and cache configuration.
13. Standard Mandarin and English server audio return valid RIFF/WAV when local TTS is healthy.
14. Browser fallback works when the server TTS path is unavailable.
15. TTS concurrency is bounded (`TTS_CONCURRENCY`).
16. Repeated engine failures open the circuit breaker for a bounded cooldown rather than spawning repeated failing processes.
17. Hashed WAV disk cache respects configured size/TTL and is mounted to the dedicated `ttscache` volume in pilot Compose.
18. `/metrics` exposes TTS successes, failures, disk-cache hits and circuit state.
19. Dialect cards do not pretend the Mandarin TTS voice is a validated dialect voice.
20. The legacy GET audio endpoint remains only for compatibility and emits a deprecation header.

## RBAC / data acceptance
21. Manager cannot read learning statistics outside their own department.
22. Editor can manage approved learning terminology but cannot access global employee analytics.
23. Admin actions remain auditable.
24. Corporate OIDC group and department claims are validated with real pilot identities before sign-off.

## Operations evidence
Run and retain output from:
```bash
bash scripts/static_preflight.sh
python scripts/pilot_preflight.py
python scripts/oidc_config_check.py
MGC_BASE_URL=http://localhost:8080 python scripts/container_smoke.py
MGC_BASE_URL=http://localhost:8080 python scripts/it_acceptance_v53.py
python scripts/load_smoke.py --base-url http://localhost:8080 --requests 500 --workers 20 --username <pilot-user> --password <redacted> --include-audio
bash scripts/backup_postgres.sh
bash scripts/restore_rehearsal.sh backups/<dump>
```

Also retain `docker compose ps`, application-image digest and redacted configuration evidence.

## Production boundary
This is a controlled pilot acceptance suite, not a capacity/security certification. Corporate rollout still requires real IdP testing, approved ingress/TLS, secrets management, centralized rate limiting/WAF if horizontally scaled, SIEM retention, PostgreSQL HA/PITR policy, SCA/container scanning and security review/pentest.
