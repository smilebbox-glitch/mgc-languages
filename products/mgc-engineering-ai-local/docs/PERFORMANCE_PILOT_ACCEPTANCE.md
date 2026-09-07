# v6.0.4 Performance Pilot Acceptance

A controlled pilot may claim performance acceptance only after all of the following are recorded on the target corporate host:

- Docker image build and runtime acceptance PASS;
- Dockle/image scan PASS;
- target PostgreSQL topology identified;
- Pilot dataset volume reached or formally waived by IT/R&D owner;
- `make performance-preflight` PASS;
- p50/p95/p99 recorded for the agreed read-only engineering scenarios;
- Pilot ordinary API p95 <= 500 ms or approved exception documented;
- reconciliation p95 <= 10 s or approved exception documented;
- error rate <= 1%;
- no OOM/restart event during steady-state test;
- DB connection pool remains below configured ceiling;
- worker backlog drains after burst test;
- Qdrant/Redis health remains within local SLO;
- fail-closed ACL/reconciliation behavior verified under concurrent load;
- CPU-only degraded-inference scenario verified;
- capacity envelope and recommended worker/concurrency values signed by IT/SRE owner.

`READY_FOR_CONTROLLED_PILOT` from data reconciliation and performance acceptance are separate gates. Both are required before a real engineering pilot is declared ready.
