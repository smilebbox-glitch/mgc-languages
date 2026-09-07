# MGC Engineering AI Local v6.3.23 — Automated Release Acceptance Pipeline

## Purpose

v6.3.23 связывает v6.3.21 Production Certification и v6.3.22 Production Load Certification в один fail-closed release-acceptance contract. Новая версия не добавляет automotive business domain и не меняет database schema: application **6.3.23**, schema **6.3.13**.

## Evidence flow

1. На target environment создаётся подписанное load evidence v6.3.22/v6.3.23 contract: mixed BOM/WI/Object 360/Digital Thread/RAG workload, p50/p95/p99, error rate, throughput, DB/queue saturation.
2. Сохраняется target-host failover/LB/RTO/RPO evidence.
3. `release_acceptance_pipeline.py` проверяет detached signature load evidence и рассчитывает absolute SLO decision через существующий Production Certification contract.
4. Если задан approved baseline, pipeline проверяет его canonical digest, detached signature, human approval reference, profile/schema и release ordering.
5. Выполняется relative regression gate относительно approved baseline.
6. Создаётся canonical release-acceptance JSON с parent acceptance hash и chain sequence.
7. Acceptance JSON при наличии signing key получает detached OpenSSL signature.
8. Даже `GO` остаётся только technical acceptance: `production_authorized=false`, human change-control обязателен.

## Regression policy

Default v6.3.23 policy блокирует release, если по сравнению с approved baseline:

- p95 latency выросла более чем на **15%**;
- p99 latency выросла более чем на **20%**;
- error rate вырос более чем на **0.2 percentage points** (`+0.002` absolute);
- throughput упал ниже **90%** baseline;
- maximum DB-pool saturation вырос более чем на **0.10 absolute**;
- RTO ухудшился более чем на **20%**;
- RPO ухудшился более чем на **20%**.

Absolute profile SLO v6.3.21 и relative regression gate v6.3.23 должны пройти одновременно. Это предотвращает ситуацию, когда новый release остаётся внутри широкого SLO, но заметно деградирует относительно последнего утверждённого release.

## Approved baseline contract

Baseline schema: `mgc-approved-release-baseline-v1`.

Baseline участвует в `GO` только если:

- canonical SHA-256 корректен;
- detached signature проверена public key;
- `technical_decision=GO`;
- `human_approved=true`;
- есть непустой change/approval reference;
- profile и DB schema совпадают с текущим certification profile;
- baseline принадлежит той же major/minor release line;
- baseline старше текущего release.

### Bootstrap

Для первого внедрения разрешён explicit bootstrap baseline. Он допустим только когда:

- текущий technical certification уже `GO`;
- release acceptance имеет `CONDITIONAL` исключительно из-за отсутствия `APPROVED_BASELINE`;
- оператор использует точное подтверждение `BOOTSTRAP_APPROVED_BASELINE`;
- указан human approval reference;
- bootstrap source имеет chain sequence 1.

Same-release baseline без этих bootstrap условий запрещён.

## Commands

Static validation:

```bash
make release-acceptance-preflight
```

Controlled live pipeline:

```bash
MGC_RELEASE_ACCEPTANCE_CONFIRM=YES \
PROFILE=30 \
BASE_URL=https://mgc.example \
PROJECT_CODE=CERT_FIXTURE \
PART_NUMBER=TEST_PART \
TOPOLOGY=/secure/evidence/topology.json \
EVIDENCE=/secure/evidence/failover-rto-rpo.json \
OUTPUT=/secure/evidence/release-acceptance-v6.3.23.json \
LOAD_SIGNING_KEY=/secure/keys/load.pem \
ACCEPTANCE_SIGNING_KEY=/secure/keys/acceptance.pem \
BASELINE=/secure/evidence/approved-baseline-v6.3.22.json \
BASELINE_SIGNATURE=/secure/evidence/approved-baseline-v6.3.22.json.sig \
BASELINE_PUBLIC_KEY=/secure/keys/baseline-public.pem \
make release-acceptance
```

`release-acceptance` automatically runs the non-destructive load certification. It does **not** silently inject host/DB failures.

If the company intentionally wants a disruptive failover command inside the same controlled run, both are required:

```bash
MGC_RELEASE_ACCEPTANCE_DISRUPTIVE_CONFIRM=YES
MGC_RELEASE_ACCEPTANCE_FAILOVER_CMD='<approved corporate drill command>'
```

## Baseline promotion

A technical acceptance does not promote itself. Human change authority must explicitly promote it:

```bash
make acceptance-baseline-promote \
  ACCEPTANCE=/secure/evidence/release-acceptance-v6.3.23.json \
  ACCEPTANCE_SIGNATURE=/secure/evidence/release-acceptance-v6.3.23.json.sig \
  ACCEPTANCE_PUBLIC_KEY=/secure/keys/acceptance-public.pem \
  APPROVAL_REFERENCE=CHG-12345 \
  CONFIRM=APPROVE_BASELINE \
  BASELINE_OUTPUT=/secure/evidence/approved-baseline-v6.3.23.json \
  BASELINE_SIGNING_KEY=/secure/keys/baseline.pem
```

For the first ever baseline, use `CONFIRM=BOOTSTRAP_APPROVED_BASELINE` only under the bootstrap conditions above.

## Chain verification

Acceptance schema: `mgc-release-acceptance-evidence-v1`.
Chain schema: `mgc-release-acceptance-chain-v1`.

Each acceptance contains:

- sequence;
- `parent_acceptance_sha256`;
- canonical digest of current load evidence;
- digest of target-host acceptance evidence;
- technical certification decision;
- baseline comparison and regression checks.

Verification:

```bash
make acceptance-chain-verify \
  PUBLIC_KEY=/secure/keys/acceptance-public.pem \
  ACCEPTANCE_FILES='acceptance-v6.3.23.json acceptance-v6.3.24.json'
```

The verifier rejects schema/digest/signature/sequence/parent mismatch.

## Safety boundaries

- No private signing key is stored in the release package.
- Secrets/credentials remain environment/runtime inputs.
- Pipeline never sets `production_authorized=true`.
- Human change control remains mandatory after technical `GO`.
- No automatic replay of non-idempotent engineering writes is introduced.
- Disruptive failover injection remains explicit opt-in.
- Packaging-time tests do not represent live corporate 15/30/100-user certification.
