# MGC Engineering AI Local v6.0.5
## Security & Enterprise Deployment Hardening

v6.0.5 — пятый этап production-hardening после Engineering Intelligence OS. Релиз не добавляет новый инженерный домен: он усиливает identity, PKI/network boundary, service-account privileges, audit governance и software supply chain перед реальным корпоративным пилотом.

### Основные изменения

- Production OIDC переведён в fail-closed режим:
  - HTTPS issuer/JWKS;
  - обязательный audience в production;
  - allowlist асимметричных JWT algorithms;
  - bounded clock skew;
  - optional ACR policy;
  - discovered JWKS host ограничен issuer host / allowlist;
  - внутренние JWT/JWKS ошибки не возвращаются клиенту.
- `trusted_headers` в production запрещён по умолчанию. Legacy opt-in требует независимый `X-MGC-Proxy-Secret`; одних `X-Forwarded-User/Groups` недостаточно.
- CORS methods/headers больше не wildcard — используются явные allowlists.
- Enterprise DB least privilege:
  - отдельная runtime DB identity для API/worker;
  - отдельная one-shot migration identity;
  - API/worker в enterprise overlay запускаются с `AUTO_MIGRATE_SCHEMA=false`;
  - `schema-migrate` выполняет DDL и завершается до запуска runtime services.
- Enterprise TLS edge:
  - TLS 1.2/1.3;
  - HSTS и security headers;
  - browser/SSO traffic отделён от machine integration channel.
- Machine integration edge требует mTLS client certificate и сохраняет backend HMAC verification как второй независимый контроль.
- Engineering Admin security endpoints:
  - `/api/v1/security/posture`;
  - `/api/v1/security/audit/export`;
  - `/api/v1/security/audit/retention`.
- Audit export:
  - NDJSON;
  - чувствительные detail keys редактируются;
  - cumulative SHA-256 export chain;
  - SHA-256 всего payload в response header.
- Audit retention:
  - minimum-retention policy;
  - preview до удаления;
  - destructive apply только с `confirm=PURGE_AUDIT`;
  - само применение retention записывается новым audit event.
- Software supply chain:
  - offline CycloneDX-style declared-component SBOM;
  - deterministic committed-secret scanner;
  - dependency lock readiness preflight;
  - Trivy/Grype build-host hook с fail-closed режимом;
  - enterprise deployment template без floating `:latest` image references.
- Добавлены threat model, enterprise security deployment runbook и least-privilege service-account policy.

### Важные границы

Packaging environment не подтверждает отсутствие CVE, не заменяет penetration test и не является formal ISO/SOC security certification. Здесь отсутствуют Trivy/Grype/Dockle и корпоративные IdP/PKI/registry/mirror. Поэтому real CVE scan, resolved image/filesystem SBOM, dependency lock/wheelhouse, Dockle, TLS/mTLS negative tests и OIDC/AD acceptance остаются обязательными corporate build/runtime gates.

Frontend `package-lock.json` не был сгенерирован искусственно: офлайн-среда не имеет metadata approved npm mirror. Enterprise CI должен создать/проверить lockfile из корпоративного npm mirror и запускаться с `MGC_REQUIRE_LOCKFILES=true`. Backend declared requirement ranges аналогично должны разрешаться в утверждённый wheelhouse/resolved SBOM.

### Развёртывание enterprise profile

Использовать `docker-compose.enterprise-security.yml` совместно с air-gap/runtime + SSO + webhook overlays. Сертификаты не входят в release; `MGC_TLS_CERT_DIR` должен указывать на защищённый каталог corporate PKI.

Runtime и migration PostgreSQL credentials должны быть разными и выдаваться DBA по принципу least privilege.
