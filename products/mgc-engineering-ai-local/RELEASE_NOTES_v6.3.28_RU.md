# MGC Engineering AI Local v6.3.28 — Integration Runtime Assurance

## Основное

v6.3.28 укрепляет эксплуатационный слой корпоративных PLM/PDM/ERP/MES/QMS-интеграций после v6.3.27. Новых перегружающих интерфейс модулей не добавлено: версия закрывает риски устаревшего кэша и recovery-deadlock.

### Добавлено и исправлено

- bounded cache staleness для интеграционного кэша;
- `mgc.integration-runtime-posture.v2` с возрастом кэша и допустимым пределом;
- stale cache больше не разрешается выдавать как допустимый cached read;
- `CACHE_STALE` и `NO_CACHED_ENGINEERING_DATA` как явные runtime-причины;
- opt-in `recovery_sync_enabled` для безопасного восстановительного source pull;
- старые v6.3.27 конфигурации сохраняют прежний fail-closed режим, если opt-in не задан;
- исправлен расчёт sync success rate: фактический успешный статус `ok` теперь учитывается как успех;
- reference contracts PLM/PDM/ERP/MES/QMS получили bounded cache policy и recovery opt-in;
- rolling/blue-green adjacent window: **6.3.27 ↔ 6.3.28**.

### Сохранено

- read-only интеграционный контракт без writeback в PLM/PDM/ERP/MES/QMS;
- immutable external object history, quarantine/replay и reconciliation;
- human-confirmed mapping registry;
- запрет автоматического выбора source-of-truth winner;
- 247 bounded-context automotive routes;
- 181/181 legacy API contracts;
- локальный/CPU-first режим и существующие BOM/WI/RAG/цеховые workflows.

### Версии

- Application: **6.3.28**
- DB schema: **6.3.13**
- Новая DB migration: **нет**
- Production authorization: **false**

### Верификация

- Backend: **630/630 PASS**, **101/101 test-файл**;
- `mgcctl verify --scope full`: **21/21 PASS**;
- Integration Certification preflight: **49/49 PASS**;
- Integration Runtime Assurance preflight: **27/27 PASS**;
- Reference contracts: **5/5 PASS**.

### Ограничение

Локальные проверки подтверждают software contracts, но не заменяют target-host сертификацию реальных Teamcenter/Windchill/3DEXPERIENCE/SAP/MES/QMS gateway. В среде упаковки Docker CLI отсутствует, а корпоративные lock/wheelhouse/image-digest/CVE approvals должны быть сформированы на целевом build-host.


## Упаковка

- controlled payload: **996 файлов**;
- ZIP: **997 members** с `BUILD_MANIFEST.json`;
- independent manifest verification: missing/extra/size/hash mismatch = **0**;
- `unzip -t`: **PASS**.
