# MGC Engineering AI Local v6.3.4 — Verification

## Verified in packaging environment

| Gate | Result |
|---|---:|
| Backend collected inventory | 369 tests / 77 files |
| Backend regression, sharded | 369/369 PASS |
| v6.3.4 Revision & Conflict | 28/28 PASS |
| Architecture Simplification | 27/27 PASS |
| Dependency Profiles | 18/18 PASS |
| Bounded Context ownership | 21/21 PASS |
| API Contract | 5/5 PASS; legacy 181/181 preserved |
| Projection Reliability | 26/26 PASS |
| Ports & Adapters | 25/25 PASS |
| Domain Integrity | 25/25 PASS |
| Docker static security | 38/38 PASS |
| Compose/runtime security | 100/100 PASS |
| Enterprise Security | 23/23 PASS |
| API authorization | 260 guarded routes; 4 explicit exceptions |
| UX acceptance | 9/9 PASS |
| Observability | 16/16 PASS |
| Corporate Deployment | 13/13 PASS |
| Game Day | 15/15 PASS |
| Secret scan | 0 committed secret candidates |
| Python compileall | PASS |
| Shell `bash -n` | PASS |
| Compose YAML parse | PASS |
| Build preflight | PASS; plain `docker compose build` supported |

## Concurrency / revision invariants verified

- stale `expected_version` is rejected with HTTP 409 instead of lost update;
- conflict response carries current authoritative record for explicit UI comparison;
- automatic merge is disabled;
- Approved/Obsolete WI creates a separate Draft revision rather than mutating the approved source;
- foreign WI revision cannot inherit reviewed translation approval;
- layout revision copies station placements into a separate Draft layout;
- same idempotency key + same payload replays the logical result; key reuse with a different payload is rejected;
- duplicate `(change_id, stage)` approval rows are rejected;
- migration fails closed when ambiguous legacy duplicate approvals exist;
- integrity/conflict operations endpoints require Engineering Admin.

## Dependency lock status

Not marked PASS:

- `frontend/package-lock.json` absent;
- Core requirements contain 21 declared ranges;
- AI requirements contain 23 declared ranges;
- Advanced requirements contain 25 declared ranges.

An approved corporate mirror/wheelhouse must resolve and pin exact artifacts before enterprise image certification.

## Not claimed as executed here

- real Docker Engine / BuildKit image build;
- production `npm ci` from an approved lockfile/mirror;
- resolved Python wheelhouse build and CVE scan;
- Dockle/Trivy/Grype scan of built images;
- target PostgreSQL migration + rollback/backup→restore rehearsal;
- real AD/OIDC and PKI/TLS/mTLS negative tests;
- target-host load/performance tests;
- production PLM/PDM/ERP/MES/QMS reconciliation;
- controlled UAT / human go-live approval.

Application/schema marker: **6.3.4 / 6.3.4**.
