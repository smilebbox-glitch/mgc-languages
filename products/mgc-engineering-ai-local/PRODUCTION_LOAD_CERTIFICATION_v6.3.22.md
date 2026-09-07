# v6.3.22 — Production Load Certification Harness

## Scope

v6.3.22 adds a reproducible, domain-aware load-certification harness for the production-acceptance contract introduced in v6.3.21. The application version is **6.3.22** and the database schema remains **6.3.13**; no database migration is introduced.

The harness is intended to measure a target environment. It does **not** turn CI, the packaging host or synthetic unit tests into a production-capacity certificate.

## Certification profiles

| Profile | Named engineers | Controlled concurrency | Minimum measured requests | Warm-up requests | HTTP p95 limit | Max error rate | DB-pool hard limit | Max oldest queued job |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 | 15 | 15 | 1,000 | 50 | 500 ms | 1.0% | < 0.95 | 300 s |
| 30 | 30 | 30 | 5,000 | 100 | 500 ms | 1.0% | < 0.95 | 180 s |
| 100 | 100 | 100 | 10,000 | 200 | 750 ms | 0.5% | < 0.90 | 120 s |

> Note: concurrency is the load-generator target, not a claim that all named engineers continuously issue simultaneous HTTP requests in normal work.

## Automotive workload mix

The default certification mix is deterministic and read-mostly:

| Operation | Weight | HTTP semantics |
|---|---:|---|
| Object 360 | 25% | GET |
| BOM versions | 20% | GET |
| Work Instructions | 20% | GET |
| Digital Thread | 15% | GET |
| RAG search | 12% | POST, audited read |
| RAG ask | 8% | POST, audited read |

No engineering-domain write operation is included in the default certification plan. This prevents a capacity test from generating ECR/ECO, WI, BOM or release mutations.

The two RAG POSTs are audited reads and can create audit records. The operator must therefore explicitly enable them with:

```bash
MGC_LOAD_ALLOW_AUDITED_POSTS=YES
```

Business write-path certification, if ever required, must use a separate tenant/project sandbox, idempotency keys and explicit cleanup. It is intentionally not part of the default production-load target.

## Explicit execution guard

A live load run is refused unless the operator sets:

```bash
MGC_LOAD_CERTIFY_CONFIRM=YES
```

This is deliberately separate from the profile and target URL so an accidental Make invocation cannot start load against a host.

## Credentials and privacy

Authentication is supplied only through ephemeral environment variables:

```bash
MGC_LOAD_API_KEY=...
# or
MGC_LOAD_BEARER_TOKEN=...
```

The harness accepts at most one of them. Real credentials must not be stored in `.env`, the repository, evidence JSON, support bundles or shell history.

The generated evidence does not retain raw project codes, part numbers or target origin. Instead it stores SHA-256 fixture/target fingerprints so the result can be correlated without unnecessarily copying business identifiers into certification artifacts.

TLS verification is enabled by default. A corporate CA can be supplied with `--ca-file`; insecure TLS bypass is not part of the certification path.

## Measurements

Warm-up requests are excluded from measured statistics. The measured phase records:

- request count and duration;
- p50, p95 and p99 latency;
- maximum latency;
- request rate;
- HTTP status distribution;
- global and per-operation error rate;
- error-budget allowance, consumption and remaining budget;
- maximum DB-pool saturation ratio;
- queue depth;
- oldest queued-job age;
- dead-letter, orphaned and expired-lease observations.

Operational saturation samples are obtained from the privacy-safe Operations summary while the load is running. Missing required measurement coverage cannot produce a technical GO.

## Tamper-evident evidence

The harness emits canonical JSON evidence using deterministic sorted UTF-8 serialization and records its SHA-256 digest. Integrity/signature metadata is excluded from the digest itself so detached signatures do not create recursive hashing.

Optional signing uses an operator/corporate PEM private key through OpenSSL:

```bash
python scripts/production_load_certify.py \
  --profile 30 \
  --base-url https://mgc.example.internal \
  --project-code '<fixture-project>' \
  --part-number '<fixture-part>' \
  --output /secure/evidence/load-30.json \
  --signing-key /secure/keys/load-certification.key.pem
```

The private key is never embedded into the evidence. The result can contain a detached `.sig`; verification occurs later with the corresponding public key.

## Production-acceptance integration

v6.3.22 removes manual copying of p95/error-rate/DB-pool numbers into the v6.3.21 acceptance evidence. The technical certification command takes the signed load result directly:

```bash
make production-certify \
  PROFILE=30 \
  TOPOLOGY=/secure/evidence/topology.json \
  EVIDENCE=/secure/evidence/target-host.json \
  LOAD_EVIDENCE=/secure/evidence/load-30.json \
  LOAD_SIGNATURE=/secure/evidence/load-30.json.sig \
  LOAD_PUBLIC_KEY=/secure/keys/load-certification.pub.pem
```

`production_certify.py`:

1. recomputes the canonical load-evidence digest;
2. verifies the detached signature with OpenSSL and the supplied public key;
3. rejects tampered evidence;
4. imports measured request count, p50/p95/p99, error rate and DB-pool saturation into the production-acceptance calculation;
5. evaluates load-specific coverage, error-budget and saturation checks together with topology, authority, failover, RTO and RPO evidence.

Decision semantics:

- complete valid signed measurements that meet all technical gates may contribute to `GO`;
- missing/unsigned load evidence remains `CONDITIONAL`;
- invalid signature, tampering, failed SLO, unsafe saturation, missing required workload coverage or failed authoritative/failover evidence produces `NO_GO` as applicable.

A technical `GO` still has `production_authorized=false` and requires an approved human change window. The load harness never self-authorizes a deployment.

## Make targets

```bash
make production-load-certification-preflight

MGC_LOAD_CERTIFY_CONFIRM=YES \
MGC_LOAD_ALLOW_AUDITED_POSTS=YES \
MGC_LOAD_BEARER_TOKEN='<ephemeral-token>' \
make production-load-certify \
  PROFILE=30 \
  BASE_URL=https://mgc.example.internal \
  PROJECT_CODE='<fixture-project>' \
  PART_NUMBER='<fixture-part>' \
  OUTPUT=/secure/evidence/load-30.json \
  SIGNING_KEY=/secure/keys/load-certification.key.pem
```

`PROFILE`, target host and fixture values are intentionally operator-supplied. Do not use example values as production evidence.

## Verification in the release environment

The release verifies the load-calculation logic, workload mix, concurrency contracts, canonical hashing, signature verification and acceptance integration. An end-to-end cryptographic test generated an ephemeral RSA keypair, signed canonical evidence and obtained a technical `GO` only after public-key verification.

This does **not** claim that a real target deployment has been load-certified.

## Not claimed by v6.3.22 packaging

The source-package verification does not claim:

- a live 15/30/100-engineer load run against corporate infrastructure;
- actual production p50/p95/p99 or throughput;
- actual PostgreSQL/evidence failover under concurrent user load;
- external-LB host-loss behavior under load;
- measured production RTO/RPO;
- corporate CVE/image acceptance;
- human Production GO.

Those are target-host acceptance activities and must be retained with the signed evidence used for the production decision.
