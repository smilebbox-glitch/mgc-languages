# Security decisions — v5.2 pilot

- **Architecture:** retain a modular monolith for pilot. No microservices are added without load/ownership/compliance justification.
- **Database:** PostgreSQL is mandatory for pilot; SQLite remains a development fallback.
- **Schema:** Alembic migrations are authoritative in pilot; runtime `create_all` is disabled.
- **Authentication:** corporate OIDC is target state; local auth exists for technical sandbox only.
- **Authorization:** RBAC is server-enforced. Manager analytics are additionally scoped by department; Admin is global.
- **Organization mapping:** OIDC department claim is configurable because IdP schemas differ by company.
- **Sessions:** HttpOnly cookies with CSRF protection, configurable TTL and Secure/SameSite flags.
- **Edge:** only Nginx/approved ingress is host-published. App/DB are internal.
- **Secrets:** env-based in package, but production target is an enterprise secret store.
- **Rate limiting:** in-memory limiter is adequate only for one/few-instance pilot; production target is gateway/WAF/Redis-class centralized control.
- **Audit:** privileged content, role and department changes are audited; source IP is not stored in clear text.
- **Pronunciation privacy:** pilot TTS is local/offline. Learning phrases are not sent to a third-party speech API.
- **TTS availability:** loss of server TTS degrades audio to browser fallback rather than taking the whole service out of readiness.
- **TTS quality:** eSpeak NG is chosen for deterministic offline availability, not final human-like voice quality. A corporate neural TTS may replace the backend later behind the same API.
- **Learning transliteration:** Russian reading approximations are explicitly non-authoritative to avoid institutionalizing incorrect pronunciation.
- **Backups:** checksummed backups and isolated restore rehearsal are part of pilot evidence; enterprise production moves scheduling/PITR to DBA tooling.

## v5.3 pronunciation privacy decisions
- New pronunciation requests use POST bodies to reduce phrase leakage into URLs/access logs.
- Voice recording is out of scope. `Permissions-Policy` denies microphone access.
- TTS disk cache uses hashed filenames, bounded size and bounded retention.
- Cache is an internal pilot volume; do not mount it as a public/static directory.
- Standard-Mandarin TTS is not reused to impersonate regional dialect audio.
- TTS subprocess concurrency and circuit breaking reduce process-exhaustion risk during engine failure.
