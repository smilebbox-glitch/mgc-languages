# MGC Languages v5.1 — Pilot / IT Hardening

- PostgreSQL-first pilot Compose with isolated backend network and Nginx-only host exposure.
- Alembic baseline migration; pilot disables automatic schema creation.
- OIDC mode with discovery metadata and group-to-role mapping; local auth retained for sandbox.
- Configurable session TTL, Secure/SameSite cookies and controlled self-registration.
- CSRF protection for authenticated state-changing API calls.
- Trusted Host and optional CORS allowlists; CSP/HSTS/security response headers.
- Request IDs, JSON request logs and internal Prometheus-compatible metrics.
- Admin audit log and system configuration summary.
- Login/content/game/XP rate limits for single-instance pilot.
- PostgreSQL pool tuning via environment.
- Backup/restore scripts with checksum and 14-day default retention.
- Non-root/read-only/capability-dropped app container in pilot topology.
- CI/static preflight and new negative security tests.
- Fixed missing `rate_limit` / `audit_event` implementations from v5.0 packaging.
