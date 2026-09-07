# MGC Engineering AI Local v6.3.15 — Operational Resilience & Self-Diagnostics

## Goal

Keep the deterministic engineering core usable when optional runtime dependencies degrade, while preventing retry storms against failing infrastructure. v6.3.15 does not move engineering authority into Redis, Qdrant, AI servers, CAD gateways or circuit-breaker state.

## Resilience boundary

- PostgreSQL and authoritative evidence storage remain Core data dependencies.
- Circuit-breaker state is process-local operational protection only; restarting a process resets it.
- Qdrant, local LLM/VLM and native CAD conversion are optional enrichment/heavy-compute capabilities.
- Redis/Celery loss pauses managed asynchronous dispatch but does not erase `ComputeJob` state from PostgreSQL.
- No circuit breaker authorizes an engineering decision, approval, release or replay.

## Circuit breaker

`backend/app/core/resilience.py` implements bounded per-process dependency circuits with three states:

- `closed` — calls are permitted;
- `open` — repeated calls are suppressed after the configured failure threshold;
- `half_open` — one probe is permitted after the cooldown; success closes the circuit, failure opens it again.

Default policy:

- `RESILIENCE_ENABLED=true`;
- `RESILIENCE_FAILURE_THRESHOLD=3`;
- `RESILIENCE_OPEN_SECONDS=30`;
- `RESILIENCE_STRICT_DEPENDENCY_READINESS=false`.

Legacy/partial Settings objects that do not define the new readiness switch remain fail-closed for compatibility; the real v6.3.15 configuration explicitly selects brownout semantics.

## Graceful degradation

### Qdrant

When semantic infrastructure is unavailable or the Qdrant circuit is open:

- semantic indexing is skipped rather than blocking authoritative document ingestion;
- semantic search falls back to PostgreSQL lexical/metadata retrieval;
- Qdrant remains a rebuildable projection and never becomes engineering truth.

### Local LLM

When local AI is unavailable:

- AI synthesis is skipped;
- RAG still returns accessible evidence and deterministic retrieval results;
- BOM/WI/document/change records remain usable;
- translation requests remain explicit failures rather than silently inventing translations.

### VLM / drawing vision

When VLM is unavailable:

- deterministic drawing/CAD analysis remains available;
- VLM transcription/consensus is marked unavailable/brownout;
- AI output never overwrites deterministic engineering evidence.

### Native CAD gateway

When the CAD gateway circuit is open:

- conversion requests fail with a service-unavailable posture;
- the immutable source document remains available;
- BOM, WI, document metadata and Digital Thread are not disabled.

### Redis / Celery

Managed background job dispatch checks the Redis circuit before publishing. Publish failures are recorded by the breaker. PostgreSQL retains the managed job ledger and v6.3.13 fencing/recovery semantics, so broker loss does not turn Redis into a source of job truth.

## Readiness semantics

v6.3.15 separates **Core readiness** from **optional capability health**.

With the default v6.3.15 configuration:

- PostgreSQL schema + authoritative evidence storage gate Core readiness;
- Redis/Qdrant/graph/object-store failures are exposed in diagnostics and can drive brownout without automatically removing deterministic Core access;
- `RESILIENCE_STRICT_DEPENDENCY_READINESS=true` restores strict optional-dependency readiness gating where corporate policy requires it.

## Operations and self-diagnostics

Engineering Admin receives:

- `GET /api/v1/operations/resilience` — sanitized breaker/brownout state;
- resilience state embedded in `/health/ready` and operations summary;
- Prometheus metrics:
  - `mgc_resilience_circuit_state`;
  - `mgc_resilience_consecutive_failures`;
  - `mgc_resilience_circuit_trips_total`;
  - `mgc_resilience_brownout`;
- `resilience.json` inside the privacy-safe support bundle.

No raw exception message, secret, endpoint credential, document content, SQL, VIN history or proprietary engineering payload is added to the support bundle by this feature.

## Non-goals

v6.3.15 does not:

- claim distributed consensus for breaker state;
- auto-repair PostgreSQL/evidence corruption;
- auto-replay human decision-producing engineering work;
- make Qdrant/Redis/AI/CAD authoritative;
- claim production capacity or availability certification from source-level tests;
- authorize Production GO.
