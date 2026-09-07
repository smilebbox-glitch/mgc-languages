# Release Notes — «Окно в Китай» Pilot v1.3

## Operations & Security

### Новое

- `X-Request-ID` correlation layer для API;
- rate limiting: read / expensive analysis / admin mutation buckets;
- SIEM-ready security events для authorization/rate-limit/outbound-policy событий;
- append-only admin audit trail с `previousHash` + SHA-256/HMAC-SHA256;
- `/api/admin/audit`;
- `/api/admin/backup`;
- `/api/admin/restore`;
- backup/restore UI в `/admin`;
- audit view + chain status в `/admin`;
- Prometheus counters для rate-limit и audit writes;
- host deployment preflight;
- post-start container smoke checks;
- CycloneDX SBOM generator из package lock;
- online `npm audit` gate;
- generic CI security gate и optional Trivy image scan;
- reverse-proxy template передаёт server-generated request ID.

### Усилено

- runtime configuration changes теперь попадают в audit trail;
- outbound policy blocks дают security events;
- admin operations имеют отдельные rate-limit buckets;
- application version обновлена до `1.3.0-pilot`;
- Docker build выполняет offline pilot preflight до application build.

### Ограничения

- встроенный rate limiter хранится в памяти процесса и предназначен только для single-instance pilot;
- локальная audit rotation сохраняет текущий файл и один `.1`; corporate retention должен быть вынесен в SIEM/backup;
- online vulnerability advisory check зависит от сетевого доступа CI к npm registry/advisory service;
- image CVE scan требует Trivy или корпоративный scanner;
- runtime backup не является полным DR backup: secrets и audit намеренно исключены.
