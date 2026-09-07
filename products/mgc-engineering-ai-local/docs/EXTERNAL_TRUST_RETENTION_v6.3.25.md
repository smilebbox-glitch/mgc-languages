# MGC Engineering AI Local v6.3.25 — External Trust Anchoring & Evidence Retention Governance

## Purpose

v6.3.25 hardens the v6.3.24 acceptance-evidence registry so its integrity can be proven beyond the local filesystem. It adds bounded signing-key validity, minimum-retention/legal-hold governance, immutable registry checkpoints, external tip-hash anchoring, WORM/object-lock receipt integration and offline auditor verification bundles.

This release does **not** claim that a corporate WORM system, timestamp/notary service, HSM/KMS or legal-retention platform was executed in the packaging environment. Those controls are integrated through fail-closed external adapter contracts and must be exercised on the target environment.

## Signing-key lifecycle

A newly registered public key receives a bounded validity window. Default policy:

- validity: 180 days;
- rotation warning: 30 days before expiry;
- rotation uses a new immutable `key_id`;
- revocation remains append-only;
- expired/revoked keys cannot sign new evidence.

Historical verification uses the key state and validity window at the evidence-registration timestamp. A later expiry or revocation therefore does not invalidate evidence that was validly registered earlier.

Example:

```bash
python scripts/release_provenance_registry.py \
  --registry /controlled/release-provenance \
  key-register \
  --key-id release-2026-q4 \
  --public-key /controlled/keys/release-2026-q4.pub.pem \
  --valid-days 180 \
  --rotation-warning-days 30
```

Private keys remain forbidden in the registry.

## Retention policy

Retention is a **minimum retention** contract. The application never automatically destroys acceptance evidence because removing a referenced content-addressed object would break cryptographic replay.

```bash
make release-provenance-retention-set \
  REGISTRY=/controlled/release-provenance \
  POLICY_ID=R-10Y \
  RETENTION_JSON='{"load":1460,"acceptance":3650,"baseline":3650}'
```

The ledger metadata is permanent by application policy. Any future physical destruction after the minimum retention period belongs to an approved external records-management process.

## Legal hold

A hold can target a release or a specific object SHA-256:

```bash
RELEASE=6.3.25 make release-provenance-hold-place \
  REGISTRY=/controlled/release-provenance \
  HOLD_ID=AUDIT-2026-09 \
  REASON='external audit'
```

Release is another immutable event:

```bash
make release-provenance-hold-release \
  REGISTRY=/controlled/release-provenance \
  HOLD_ID=AUDIT-2026-09 \
  REASON='audit closed'
```

No event or evidence object is rewritten when a hold changes state.

## Registry checkpoints

A checkpoint is created only after full registry cryptographic verification passes. It binds:

- covered tip sequence;
- covered tip SHA-256;
- registry summary;
- retention posture;
- signing-key lifecycle;
- `production_authorized=false`.

```bash
make release-provenance-checkpoint REGISTRY=/controlled/release-provenance
```

The checkpoint JSON is itself stored as a content-addressed registry object, then referenced by `CHECKPOINT_CREATED`.

## External tip anchoring

MGC does not shell-expand an arbitrary operator string. The adapter is supplied as a JSON argv array and runs with `shell=False` and a minimized environment.

The adapter receives JSON on stdin containing:

```json
{
  "schema": "mgc-release-anchor-request-v1",
  "tip_sequence": 42,
  "tip_sha256": "...",
  "requested_at": "..."
}
```

It must return a receipt whose tip sequence/hash exactly match the request. A mismatched receipt is rejected before any anchor event is appended.

```bash
make release-provenance-anchor \
  REGISTRY=/controlled/release-provenance \
  ADAPTER_COMMAND_JSON='["/opt/company/bin/mgc-anchor-adapter"]'
```

Typical corporate adapters may wrap an RFC3161 timestamp authority, enterprise transparency log, HSM-backed notary, SIEM append-only ledger or another independently controlled service.

## WORM / object-lock integration

WORM sealing operates on the latest verified checkpoint object. The adapter receives object SHA-256, exact byte size, requested retention date, object-lock mode and whether a legal hold is active.

The receipt is accepted only when:

- the external service confirms lock/storage;
- returned object SHA-256 matches the checkpoint;
- returned retention is not shorter than requested;
- receipt has a stable external identifier.

```bash
make release-provenance-worm-seal \
  REGISTRY=/controlled/release-provenance \
  ADAPTER_COMMAND_JSON='["/opt/company/bin/mgc-worm-adapter"]' \
  RETAIN_DAYS=3650 \
  LOCK_MODE=COMPLIANCE
```

The receipt itself is content-addressed and chained into the provenance ledger.

## Governance verification

```bash
make release-provenance-governance REGISTRY=/controlled/release-provenance
```

Possible results:

- `PASS` — registry valid and no governance warning is present;
- `CONDITIONAL` — cryptographic registry is valid, but optional external anchor/WORM/checkpoint/rotation evidence is incomplete or due;
- `FAIL` — registry integrity failed, required external trust is absent, receipt binding is invalid, or there is no usable signing key.

Production deployments may configure external anchor/WORM as mandatory. Even `PASS` never sets `production_authorized=true`.

## Offline auditor bundle

```bash
make release-provenance-auditor-export \
  REGISTRY=/controlled/release-provenance \
  OUTPUT=/controlled/audit/mgc-release-auditor-v6.3.25.zip
```

The bundle contains:

- all provenance events;
- all referenced content-addressed objects;
- public verification keys already present as registry objects;
- audit report;
- governance status;
- a per-file SHA-256 manifest.

It does **not** contain private keys.

An auditor can verify it without access to the live MGC registry:

```bash
make release-provenance-auditor-verify \
  BUNDLE=/controlled/audit/mgc-release-auditor-v6.3.25.zip
```

Verification rejects duplicate/unsafe ZIP members, path traversal, symlinks, manifest differences, object tampering, event-chain tampering and signature replay failures.

## Engineering Admin API

`GET /api/v1/operations/release-provenance` remains Engineering-Admin-only. v6.3.25 adds a privacy-safe governance section with:

- governance status;
- checkpoint count/freshness;
- external anchor provider/id/freshness;
- WORM receipt id/retention/mode;
- key lifecycle status;
- retention/legal-hold summary.

Filesystem paths, public-key bytes, raw evidence and adapter commands are not returned.

## Trust boundary

Application: `6.3.25`  
Engineering DB schema: `6.3.13`  
Database migration: none.

The local registry remains tamper-evident rather than root-proof. Production-grade trust requires independently administered WORM/object-lock storage and/or an external anchor whose control plane is outside the MGC host. HSM/KMS private-key custody remains an external corporate responsibility.
