# MGC Engineering AI Local v6.3.24 — Acceptance Evidence Registry & Release Provenance Ledger

## Purpose

v6.3.24 turns the signed release-acceptance artifacts from v6.3.22–v6.3.23 into a controlled, append-only release-evidence registry. The registry is **operational release evidence**, not engineering source-of-truth data and not a substitute for PostgreSQL/evidence-storage authority fencing.

The registry provides:

- append-only event history with monotonically increasing sequence numbers;
- SHA-256 parent chaining between registry events;
- content-addressed immutable objects for public keys, acceptance JSON, approved baselines, load evidence, failover evidence and detached signatures;
- public-key registration, rotation and revocation;
- cryptographic replay of signed artifacts using the key state that was active at the time of registration;
- cross-version metric comparison;
- one audit report covering release decisions, approved baselines and trust-key lifecycle.

## Storage model

A registry root contains:

```text
<registry>/
  .append.lock
  events/
    00000001-<event_sha256>.json
    00000002-<event_sha256>.json
    ...
  objects/sha256/
    <object_sha256>
```

Event files are created with exclusive-create semantics and never overwritten by the application. Objects are named by SHA-256; if an object already exists, its bytes must still match its name. Symlinks anywhere in the controlled provenance path are rejected fail-closed.

The `.append.lock` file is coordination metadata only. Linux `flock(LOCK_EX)` serializes concurrent appenders so two release processes cannot allocate the same sequence concurrently.

## Event types

- `REGISTRY_INITIALIZED`
- `KEY_REGISTERED`
- `KEY_REVOKED`
- `ACCEPTANCE_REGISTERED`
- `BASELINE_REGISTERED`
- `LOAD_EVIDENCE_REGISTERED`
- `FAILOVER_EVIDENCE_REGISTERED`

Every event includes `sequence`, `parent_event_sha256`, actor, timestamp, object references and a canonical SHA-256 digest.

## Trust-key lifecycle

Private keys are never accepted into the registry. Only PEM public keys may be registered.

A `key_id` is immutable: rotation uses a **new key_id**. Revocation creates a new `KEY_REVOKED` event; it does not rewrite the historical `KEY_REGISTERED` record.

During full verification, the ledger is replayed in sequence. A signed acceptance/baseline/load artifact is valid only if its `key_id` was ACTIVE at that sequence. Therefore:

- an acceptance registered before key revocation remains historically verifiable;
- new artifacts signed with the revoked key are rejected;
- a later replacement key can verify subsequent releases without invalidating old evidence.

## Initialization

```bash
make release-provenance-init \
  REGISTRY=/controlled/release-provenance \
  REGISTRY_ID=mgc-production-release-ledger
```

Register a public verification key:

```bash
make release-provenance-key-register \
  REGISTRY=/controlled/release-provenance \
  KEY_ID=release-2026-q3 \
  PUBLIC_KEY=/controlled/keys/release-2026-q3.pub.pem
```

Revoke it later without deleting history:

```bash
make release-provenance-key-revoke \
  REGISTRY=/controlled/release-provenance \
  KEY_ID=release-2026-q3 \
  REASON='scheduled rotation'
```

## Registering evidence

Direct CLI example:

```bash
python scripts/release_provenance_registry.py \
  --registry /controlled/release-provenance \
  acceptance-register \
  --document release-acceptance.json \
  --signature release-acceptance.json.sig \
  --key-id release-2026-q4
```

The v6.3.23 acceptance pipeline can now append automatically when both variables are supplied:

```bash
RELEASE_PROVENANCE_REGISTRY=/controlled/release-provenance \
RELEASE_PROVENANCE_KEY_ID=release-2026-q4 \
MGC_RELEASE_ACCEPTANCE_CONFIRM=YES \
make release-acceptance
```

Baseline promotion supports the same optional registry binding through `--provenance-registry` and `--provenance-key-id`.

## Verification

```bash
make release-provenance-verify REGISTRY=/controlled/release-provenance
```

Verification checks:

1. event schema/type;
2. exact sequence order;
3. parent hash;
4. event filename = sequence + canonical event SHA-256;
5. every referenced object exists;
6. every object size and SHA-256 match;
7. public-key objects contain no private-key material;
8. key registration/revocation semantics;
9. acceptance/baseline/load canonical digest;
10. detached OpenSSL signature using the key that was ACTIVE at the registration sequence.

Any mismatch yields `FAIL`.

## Cross-version regression query

```bash
make release-provenance-compare \
  REGISTRY=/controlled/release-provenance \
  PROFILE=30 \
  RELEASE_A=6.3.23 \
  RELEASE_B=6.3.24
```

The comparison reports p95, p99, error rate, throughput, DB-pool saturation and RTO/RPO deltas. This is an audit/query surface; release acceptance policy remains enforced by the v6.3.23 acceptance pipeline.

## Audit report

```bash
make release-provenance-audit \
  REGISTRY=/controlled/release-provenance \
  OUTPUT=/controlled/audit/mgc-release-audit.json
```

The report includes registry verification, trust-key status, releases, registered acceptance decisions, approved baselines and evidence counts. It never sets `production_authorized=true`.

## Engineering Admin API

When explicitly enabled:

```text
RELEASE_PROVENANCE_REGISTRY_ENABLED=true
RELEASE_PROVENANCE_REGISTRY_PATH=/data/storage/.mgc-release-provenance
```

`GET /api/v1/operations/release-provenance` returns only a privacy-safe structural summary: registry status, tip sequence/hash, event counts, release count, active/revoked key IDs and operator guidance. Raw evidence, signatures, public-key bytes and filesystem paths are not returned.

Full detached-signature replay remains a CLI/release-engineering operation rather than an API request path.

## Security boundary

The registry is **tamper-evident**, not magical tamper-proof storage against an administrator/root user who can rewrite the whole filesystem and all external anchors. Production deployment should place it on controlled append-only/WORM-capable storage, preserve backups/checkpoints and separately protect the current tip hash. v6.3.24 does not claim WORM hardware or external notarization was tested in the packaging environment.

## Database schema

Application: `6.3.24`  
Engineering database schema: `6.3.13`

No database migration is introduced by v6.3.24.
