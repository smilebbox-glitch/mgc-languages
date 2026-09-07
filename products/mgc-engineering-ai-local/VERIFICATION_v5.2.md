# Verification — MGC Engineering AI Local v5.2.0

## Release scope

Engineering Knowledge Memory on top of v5.1 Engineering Change Intelligence and v5.0 Engineering Digital Thread Explorer.

Implemented and verified:

- ACL-safe historical case collection across ECR/ECO, 8D, Process Defects, Design Review and deterministic Validation Issues;
- human-curated `EngineeringLesson` storage with `draft / validated / archived` lifecycle;
- deterministic CPU-only similarity score with explicit `why_similar` factors;
- project scope and ACL-safe accessible-portfolio scope;
- recurrence detection between open engineering problems and closed/reusable historical cases;
- Ask Engineering Memory deterministic synthesis from ranked historical cases;
- whole-case fail-closed behavior when any linked evidence is hidden;
- Engineering Admin validation/archive governance for Lessons Learned;
- validation requires explicit outcome and effectiveness;
- validated lesson provenance is retained when archived;
- compact Project Workspace UI with no new global navigation item;
- additive/idempotent v5.2 schema wrapper; existing v4.9-v5.1 data remains intact.

## Automated verification

- Backend regression: **159/159 PASS**.
- Dedicated v5.2 Engineering Knowledge Memory scenarios: **5/5 PASS**.
- v5.2 schema migration/idempotency scenario: **1/1 PASS**.
- Human-facing API authorization preflight: **141/141 routes enforce `get_identity`**.
- Explicit API exceptions remain limited to `/health` and the HMAC-signed machine webhook.
- Dockerfile/Dockle-style static security preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **82/82 PASS**.
- Docker Compose YAML parse: **12/12 PASS**.
- TypeScript/TSX transpile syntax check: **PASS**.
- Shell syntax checks: **PASS**.
- Docker build source/context preflight: **PASS**; plain `docker compose build` is structurally supported.

## Knowledge-governance invariants

- A historical analogue is not automatically a recommendation.
- Similarity does not prove equal root cause.
- Only a human-validated lesson is marked `VALIDATED`.
- A validated lesson remains advisory and does not approve engineering/release decisions.
- Non-admin users cannot silently modify or archive a validated lesson.
- Portfolio search cannot widen Project, Manufacturing Area or Document permissions.
- Mixed visible/hidden evidence makes the whole historical case invisible to that caller.
- Source records remain authoritative; EngineeringLesson stores a reusable summary only.

## Runtime

The deterministic Engineering Knowledge Memory core works on CPU and does not require a GPU or generative model. No runtime model download is introduced by v5.2.

## Environment limitation

A real Docker image build, runtime container acceptance and Dockle image-layer scan were **not executed in this packaging environment** because Docker daemon/CLI and Dockle are unavailable here. They are intentionally not reported as passes.

Required gate on the approved corporate build host:

```bash
docker compose build
make dockle
make acceptance
```
