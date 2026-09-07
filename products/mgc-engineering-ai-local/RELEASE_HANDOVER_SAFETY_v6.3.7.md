# MGC Engineering AI Local v6.3.7
# Engineering Release Handover & Integration Safety

## 1. Purpose
Передать уже released Engineering Release Package во внешнюю authority system безопасно и доказуемо, не превращая существующие read-connectors в неконтролируемые write-connectors.

## 2. Boundary
```text
Released Package
      |
      v
Canonical Release Manifest
      |
      v
Immutable Handover Job
      |  dry-run by default
      v
Maker/Checker + Identity Policy
      |
      v
Explicit Write Gate
      |
      v
PLM / PDM / MES Gateway
      |
      v
Receipt + Reconciliation Proof
```

No path targets PLC, robot, conveyor, torque controller, paint equipment or other machine-control endpoint.

## 3. Default posture
Write-back is off after installation. Both target-code and host allowlists are empty. A target record alone is insufficient to enable delivery.

## 4. Immutable command identity
After job creation, DB triggers prevent ordinary UPDATE of package ID, target ID, manifest/request hashes, mode, idempotency key and outbound payload. Lifecycle fields may change only through controlled services.

## 5. Write gate
A controlled write requires all of the following:
1. Released package.
2. Enabled target with `allow_write=true`.
3. Target authority domain PLM/PDM/MES.
4. `HANDOVER_WRITE_ENABLED=true`.
5. Target code allowlisted.
6. Gateway hostname allowlisted.
7. HTTPS in production.
8. Target declares idempotency support.
9. Human maker-checker authorization.
10. Enterprise Identity Policy allows the action.
11. Current Release Manifest hashes still equal the immutable job hashes.
12. Retry budget not exhausted.

## 6. Idempotency and retry
A target+idempotency-key identifies one immutable outbound command. Reusing the key with another payload is rejected. Network retry uses the same key and command hash. This provides controlled at-least-once transport with idempotent target semantics, not a false distributed exactly-once claim.

## 7. Receipt and reconciliation
A target may require an external receipt. Reconciliation stores external evidence and validates returned manifest/request hashes or target-state hash proof. Missing mandatory proof or a mismatch prevents `reconciled` status.

## 8. Identity separation
Service accounts may support explicitly permitted read/reconciliation operations but cannot replace human maker/checker for write authorization/execution. Privileged write actions remain subject to OIDC assurance/re-auth policies from v6.3.6.

## 9. Disaster and operational behavior
An external PLM/MES outage does not change PostgreSQL authoritative engineering state and does not invalidate the released package. Handover remains failed/pending evidence and may be retried only under the immutable command and configured retry/idempotency rules.

## 10. Operations observability
Handover health is exposed in the Engineering Admin handover summary, Operations Summary, Prometheus and the privacy-safe Support Bundle. Failed/reconciliation-failed jobs or a delivered job older than `HANDOVER_RECONCILIATION_MAX_AGE_SECONDS` without reconciliation move Operations posture to AMBER. This is an operator signal, not a reason to make optional PLM/MES connectivity authoritative over PostgreSQL Core readiness.

## 11. Production acceptance
Before enabling write: register the corporate gateway target, validate target and host allowlists, certify idempotency behavior, validate receipt/reconciliation semantics, perform negative OIDC tests, execute network-failure/retry Game Days, and obtain InfoSec/PLM/MES/Operations approval.
