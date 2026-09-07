# MGC Engineering AI Local v6.3.32 — Resilience Certification & Recovery Baselines

## Основное

v6.3.32 не добавляет новый инженерный модуль. Версия превращает resilience drills v6.3.31 в формальный межрелизный release gate.

### Добавлено

- signed live resilience-drill evidence через detached OpenSSL SHA-256 signature;
- `mgc.resilience-recovery-baseline.v1` с фактическим RTO по каждому сценарию и aggregate RTO;
- baseline создаётся только из live `PASS` evidence с verified signature и human approval;
- `mgc.resilience-drill-campaign.v1` с обязательными сценариями, profile/tier и утверждённой regression policy;
- `mgc.resilience-certification.v1` для сравнения recovery-показателей текущего и предыдущего релиза;
- автоматическое обнаружение RTO regression по ratio, absolute delta и absolute ceiling;
- fail-closed `NO_GO` при missing scenario, tamper, invalid signature, bootstrap baseline или recovery degradation;
- baseline для release `GO` должен быть строго соседним предыдущим patch-релизом (`6.3.31 → 6.3.32`);
- current drill evidence обязан совпадать с baseline/campaign по `profile` и `tier`;
- standalone `GO` report больше не считается достаточным deploy evidence;
- `mgcctl certify resilience`;
- `resilience_release_guard.py`, который повторно проверяет detached signature и детерминированно пересчитывает certification из evidence + baseline + campaign;
- rolling/blue-green deployment требует resilience certification `GO` **и полный подписанный source bundle**;
- emergency rollback новым gate не блокируется.

### Default regression policy

Для каждого обязательного сценария одновременно:

- current/baseline RTO ≤ **1.20**;
- абсолютное увеличение ≤ **5.0 s**;
- current RTO ≤ **120.0 s**.

Автоматическое ослабление policy запрещено. Изменение порогов требует нового human-approved campaign.

### Governance

- simulation не может стать baseline;
- bootstrap baseline не может дать release `GO`;
- private signing keys не сохраняются в evidence;
- certification не выполняет fault injection самостоятельно;
- root cause не утверждается автоматически;
- `production_authorized=false`;
- human release approval обязателен.

### Версии

- Application: **6.3.32**
- DB schema: **6.3.13**
- DB migration: **нет**
- Rolling/Blue-Green adjacent window: **6.3.31 ↔ 6.3.32**

## Верификация

- Backend: **668/668 PASS**, **105/105 test-файлов**.
- Full `mgcctl verify --scope full`: **25/25 PASS**.
- Resilience Certification preflight: **18/18 PASS**.
- Resilience Drill preflight: **13/13 PASS**.
- Real detached-signature baseline → campaign → certification E2E: **PASS**.
- Legacy API: **181/181 сохранены**; current routes: **247**.
- Supply-chain status remains `CONDITIONAL`; final provenance/package counts are recorded in `VERIFICATION_v6.3.32.md`.

## Упаковка

- controlled payload: **1064 файла**;
- ZIP: **1065 members** вместе с `BUILD_MANIFEST.json`;
- missing/extra/duplicate/size/SHA mismatch: **0**;
- cache artifacts / symlinks: **0**;
- ZIP CRC: **PASS**.
