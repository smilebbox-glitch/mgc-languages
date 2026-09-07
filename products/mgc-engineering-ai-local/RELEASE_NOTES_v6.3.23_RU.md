# MGC Engineering AI Local v6.3.23 — Release Notes (RU)

## Automated Release Acceptance Pipeline

v6.3.23 объединяет production SLO/capacity gate v6.3.21 и подписываемый load evidence v6.3.22 в один контролируемый release-acceptance pipeline. Версия приложения — **6.3.23**, схема БД остаётся **6.3.13**, миграция не требуется.

### Что добавлено

- единый `release_acceptance_pipeline.py` для topology + failover/RTO/RPO + signed load evidence;
- trusted approved baseline schema;
- обязательная проверка baseline canonical SHA-256 и detached signature;
- обязательный `human_approved` + change/approval reference;
- relative performance regression gate относительно последнего approved baseline;
- p95 +15%, p99 +20%, error-rate +0.002, throughput не ниже 90%, DB-pool saturation +0.10, RTO/RPO +20% thresholds;
- fail-closed release ordering/profile/schema checks;
- explicit bootstrap baseline для первого внедрения;
- canonical release acceptance SHA-256;
- detached signature acceptance report;
- parent SHA-256 + sequence acceptance chain;
- chain verifier;
- controlled wrapper, который автоматически запускает non-destructive load certification;
- disruptive failover command запускается только при отдельном `MGC_RELEASE_ACCEPTANCE_DISRUPTIVE_CONFIRM=YES`;
- технический `GO` по-прежнему не является Production Authorization.

### Verification

- backend regression: **558/558 PASS**, **96/96 test-файлов**;
- Automated Release Acceptance Pipeline preflight: **26/26 PASS**;
- focused v6.3.21/v6.3.22/v6.3.23 acceptance/rolling/blue-green regression: **62/62 PASS**;
- real crypto E2E: ephemeral RSA load signature → bootstrap signed acceptance → human-approved signed baseline → repeated acceptance with baseline regression → technical `GO` — PASS;
- legacy API **181/181** preserved;
- bounded-context routes remain **247**.

### Ограничения

Packaging environment не выполнял корпоративный live load 15/30/100, физический host-loss, PostgreSQL promotion или evidence-storage failover. v6.3.23 автоматизирует сбор/проверку/связывание этих evidence, но не подменяет target-host drill. Supply-chain и Production Authorization остаются fail-closed.

Подробности: `docs/AUTOMATED_RELEASE_ACCEPTANCE_v6.3.23.md` и `docs/VERIFICATION_v6.3.23.md`.
