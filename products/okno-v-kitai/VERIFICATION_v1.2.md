# Verification — «Окно в Китай» Pilot v1.2

Дата проверки: 2026-09-06.

## Выполненные проверки

| Проверка | Результат |
|---|---:|
| TypeScript/TSX syntax transpile | 110/110 PASS |
| Security preflight | 11/11 PASS |
| Compose YAML parse | PASS |
| package.json / package-lock.json parse | PASS |
| RBAC: disabled viewer | PASS |
| RBAC: local admin token | PASS |
| RBAC: forged proxy secret rejected | PASS |
| RBAC: trusted proxy + admin group | PASS |
| Runtime config defaults | PASS |
| Runtime config persistence/merge | PASS |
| Outbound allowed host | PASS |
| Outbound unlisted host blocked | PASS |
| Outbound HTTP policy | PASS |
| Redirect to unlisted host blocked | PASS |
| CBR CNY parser regression | PASS |
| Bank CNY parser regression | PASS |
| Server API direct fetch bypass scan | PASS |

## Security preflight assertions

1. read-only root filesystem;
2. no-new-privileges;
3. all Linux capabilities dropped;
4. localhost bind is default;
5. dedicated runtime volume exists;
6. Docker healthcheck uses readiness;
7. auth mode explicit;
8. trusted-proxy secret configurable;
9. metrics token configurable;
10. outbound allow-list configurable;
11. all server-side HTTP fetches centralized through `lib/outbound.ts`.

## Проверено статически, но требует целевой инфраструктуры

- реальный `docker compose build` на корпоративном сервере;
- TLS certificate chain;
- выбранный SSO/IdP и его group claims;
- корпоративный DNS;
- Prometheus scrape;
- Loki/ELK/Splunk ingestion;
- firewall rules;
- RAG endpoint connectivity;
- vulnerability/image scan.

Исходный архив не содержит `node_modules`; runtime image устанавливает зависимости штатно через `npm ci` в Docker build stage.
