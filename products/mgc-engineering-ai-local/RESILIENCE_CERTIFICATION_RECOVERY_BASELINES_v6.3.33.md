# MGC Engineering AI Local v6.3.33 — Resilience Certification & Recovery Baselines

## Цель

v6.3.33 превращает bounded resilience drills v6.3.31 в **межрелизный release-governance контур**. Он отвечает на вопрос не только «восстановилась ли система после отказа?», но и «не стало ли восстановление новой версии хуже утверждённого предыдущего baseline?».

Application: **6.3.33**  
Database schema: **6.3.13**  
DB migration: **none**

## Контракты

- `mgc.resilience-recovery-baseline.v1` — human-approved baseline, созданный только из live `PASS` drill evidence с проверенной detached signature;
- `mgc.resilience-drill-campaign.v1` — human-approved campaign: обязательные сценарии, profile/tier и неизменяемые regression thresholds;
- `mgc.resilience-certification.v1` — автоматическое сравнение текущего signed drill с baseline по каждому сценарию и aggregate RTO.

## RTO regression policy

По умолчанию каждый обязательный сценарий должен одновременно удовлетворять:

- `current_rto / baseline_rto <= 1.20`;
- абсолютное увеличение `<= 5.0 s`;
- абсолютный `current_rto <= 120.0 s`.

Campaign может установить более строгие значения. Автоматическое ослабление threshold во время certification запрещено. Изменение policy требует нового human-approved campaign.

## Signed drill evidence

`resilience_certify.py` подписывает и проверяет **canonical JSON payload** drill evidence через detached OpenSSL SHA-256 signature. В baseline/certification сохраняется только результат проверки, algorithm и SHA-256 публичного ключа; private key в evidence не переносится.

Simulation (`SIMULATED`) не может быть baseline и не может дать release `GO`.

## Approved baseline

Baseline создаётся только при:

1. live drill evidence со статусом `PASS`;
2. корректной SHA-256 integrity исходного evidence;
3. verified detached signature;
4. явном `--confirm APPROVE-BASELINE`;
5. непустой change/approval reference, timestamp и approver role.

Для release `GO` baseline должен быть **не-bootstrap и относиться строго к соседнему предыдущему patch-релизу**. Для v6.3.33 допустимый release baseline — **v6.3.32**; v6.3.31 и более старые baseline fail-closed блокируются. Bootstrap baseline разрешён только для настройки процесса и всегда блокирует production release certification.

## Approved drill campaign

Campaign фиксирует:

- target release;
- baseline SHA-256;
- profile / tier;
- список обязательных scenarios;
- RTO regression thresholds;
- human approval reference / timestamp / role.

Создание требует точного `--confirm APPROVE-CAMPAIGN`.

## Automatic release regression gate

`certify_recovery()` сравнивает baseline и current live evidence. Для каждого required scenario формируются:

- baseline RTO;
- current RTO;
- ratio;
- absolute delta;
- PASS/FAIL относительно approved policy.

Любой missing scenario, invalid signature, tampered evidence/campaign/baseline, bootstrap baseline, несовпадение `profile/tier`, не-соседний baseline или RTO regression даёт `NO_GO`.

`GO` **не означает production authorization**. `production_authorized=false` и human release approval остаются обязательными.

## Deployment integration

Реальный `mgcctl deploy` v6.3.33 требует одновременно:

- target-host assurance PASS;
- resilience certification GO.

Rolling и Blue/Green scripts не доверяют одному `GO` report. Перед rollout они требуют report + current drill evidence + detached signature + public key + approved baseline + approved campaign; release guard повторно проверяет подпись и детерминированно пересчитывает certification. Несовпадение с переданным report даёт `NO_GO`. Emergency Blue/Green rollback намеренно не блокируется новым gate.

## CLI

```text
python scripts/resilience_certify.py sign-evidence ...
python scripts/resilience_certify.py baseline ... --confirm APPROVE-BASELINE
python scripts/resilience_certify.py campaign ... --confirm APPROVE-CAMPAIGN
python scripts/resilience_certify.py certify ... --require-go
./mgcctl certify resilience ... --require-go
./mgcctl deploy ... \
  --resilience-certification /controlled/resilience-certification.json \
  --resilience-evidence /controlled/current-drill-evidence.json \
  --resilience-evidence-signature /controlled/current-drill-evidence.sig \
  --resilience-public-key /controlled/resilience-public.pem \
  --resilience-baseline /controlled/recovery-baseline.json \
  --resilience-campaign /controlled/drill-campaign.json
```

## Safety boundary

- нет автоматического chaos/fault injection в certification;
- certification работает только с evidence уже выполненных bounded drills;
- нет автоматического root-cause attribution;
- нет automatic threshold relaxation;
- нет automatic production authorization;
- private signing keys не включаются в package/evidence;
- DB schema не меняется.
