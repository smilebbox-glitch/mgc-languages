# «Окно в Китай» — Pilot v1.2

## Основное

v1.2 переводит MVP из demo-ready состояния в production-oriented internal pilot baseline.

### Access / RBAC

- SSO-ready `AUTH_MODE=proxy`;
- доверие identity headers только при корректном `AUTH_PROXY_SECRET`;
- роли `viewer`, `editor`, `admin`;
- отдельный `ADMIN_API_TOKEN` для pre-SSO пилота;
- `/api/session`, `/api/admin/status`, `/api/admin/config`.

### Admin control plane

- новая страница `/admin`;
- runtime-переключатели ЦБ, банковских курсов, Telegram, АВТОСТАТ, китайских порталов, перевода и RAG;
- конфигурация сохраняется в `/data/runtime-config.json`;
- отдельный Docker volume `okno-runtime-data`.

### Network security

- единый server-side `safeFetch`;
- hostname allow-list;
- отдельный allow-list для HTTP внутренних endpoint;
- повторная проверка redirect target;
- redirect non-idempotent запросов блокируется;
- приложение bind по умолчанию только на `127.0.0.1`.

### Observability

- `/api/metrics` в Prometheus format;
- uptime/memory/source-state/external request metrics;
- опциональный `METRICS_TOKEN`;
- структурированные JSON-события в stdout/stderr;
- admin dashboard показывает status/latency внешних интеграций.

### Runtime / Security

- readiness теперь проверяет writable runtime volume;
- healthcheck Docker переведён на `/api/ready`;
- CSP + HSTS и существующие security headers;
- non-root/read-only/no-new-privileges/cap_drop/limits сохранены;
- Nginx reverse-proxy/TLS/SSO template добавлен.
