# MGC Engineering AI Local v6.3.27 — Real Integration Certification

## Scope

v6.3.27 formalizes vendor-neutral certification for **PLM, PDM, ERP, MES and QMS** corporate gateways. It does not embed vendor SDKs or claim certification against a specific production system without target-host evidence.

Application version: **6.3.27**  
Database schema: **6.3.13**  
Database migration: **none**

## Contract model

Each external system keeps the existing `mgc-integration-v1` data contract and declares a certification policy in `config_json.certification`:

- required domain capabilities;
- `checkpoint_mode`: `source_checkpoint` or `fingerprint`;
- degraded mode: `cached_read_only`;
- source writeback disabled;
- optional fail-closed sync enforcement;
- minimum recent sync success rate;
- maximum quarantine ratio.

Reference contracts are supplied under `ops/integrations/contracts/` for PLM/PDM/ERP/MES/QMS.

## Static certification

Static certification checks:

1. supported source domain;
2. allowed connector type for the domain;
3. exact `mgc-integration-v1` contract version;
4. credentials represented only by `*_env` references;
5. no raw token/API-key/password/client-secret/private-key in connector config;
6. HTTPS for corporate REST endpoints, with HTTP allowed only for explicitly configured localhost/integration simulator;
7. required capability declaration;
8. recommended domain fields;
9. source-system writeback disabled;
10. `cached_read_only` degraded policy;
11. recognized checkpoint mode.

A missing non-security capability declaration is `CONDITIONAL`. Security, transport, writeback or incompatible contract failures are `NO_GO`.

## Live read-only certification

`POST /api/v1/integrations/{system_id}/certify` is Engineering Admin only. A live probe is bounded to at most 50 source records and performs no source-system mutation.

The live probe validates:

- health endpoint availability;
- two reads of the same first page produce the same canonical fingerprint;
- stable and unique external IDs;
- sample records pass the existing integration contract validator;
- replay generates the same idempotency keys;
- source checkpoint is stable when required, or a deterministic local fingerprint checkpoint is produced.

The returned sample evidence does **not** include raw external IDs. External IDs and full record snapshots are represented by SHA-256 fingerprints.

## Degraded integration mode

`GET /api/v1/integrations/{system_id}/runtime-posture` returns one of:

- `ACTIVE`;
- `DEGRADED_READ_ONLY`;
- `BLOCKED`.

If an already-ingested integration loses source health, MGC can keep cached authoritative evidence readable while blocking new sync when `enforce_for_sync=true`. High quarantine ratio or low recent sync success also moves the integration into degraded read-only mode.

This does **not** make MGC authoritative over PLM/PDM/ERP/MES/QMS. `authoritative_source_mutation_allowed=false` is explicit in the runtime posture.

## Reconciliation and replay

v6.3.27 reuses and certifies the existing v6.0.2/v6.0.3 controls instead of duplicating them:

- immutable external-object versions;
- source fingerprint and modified timestamp;
- PostgreSQL serialized sync per external system;
- unique ingest idempotency key;
- quarantine with controlled replay;
- human-confirmed identifier mappings;
- EBOM↔MBOM reconciliation;
- MES genealogy reconciliation;
- QMS defect linkage;
- source-of-truth conflict detection without automatic winner selection.

## Operator CLI

Static reference contract:

```bash
./mgcctl certify integration \
  --contract ops/integrations/contracts/plm.example.json \
  --require-pass
```

Target gateway live certification:

```bash
./mgcctl certify integration \
  --contract /secure/site/plm.json \
  --live \
  --sample-limit 20 \
  --require-pass \
  --output plm-certification.json
```

Credentials remain environment references; they are not embedded in the contract JSON or certification report.

## Local simulator

`ops/integrations/plm.simulator.json` is provided only for local E2E verification with `docker-compose.integration-demo.yml` or the simulator FastAPI process. Its HTTP allowance is explicitly localhost/simulator-only and is not a production transport exception.

## Production boundary

v6.3.27 certifies the software contract and provides the target-host test harness. A real integration is not production-certified until the company executes the live contract probe against its actual gateway, verifies reconciliation on representative engineering data, records authentication/TLS/network evidence and completes the existing human-controlled release process.

`production_authorized=false` remains the default.
