# v5.0 Engineering Digital Thread Explorer — Pilot Acceptance

## Functional acceptance

1. Open a Project Workspace and expand **Engineering Digital Thread**.
2. Confirm the project view shows only entities visible to the current engineer.
3. Select a real part and depth 2–3; confirm the result shrinks to a local impact thread.
4. Confirm at least two applicable cross-domain paths are explainable from the selected part, for example requirement/V&V, process/WI, supplier, cost, ECR/ECO, architecture/interface, variant or release evidence.
5. Confirm BOM edges match the deterministic BOM source and are not inferred by AI.
6. Remove or revoke evidence and confirm the related evidence-backed node fails closed where applicable.
7. Confirm a missing drawing/CAD, requirement V&V or work instruction appears as a trace gap rather than an invented link.
8. Confirm the Explorer coverage metric does not change Project/Release Readiness.

## Access-control acceptance

Use at least two engineering identities with different Manufacturing Area / Document ACL visibility.

- Hidden documents must not appear as nodes, labels, routes or edge metadata.
- A supplier/architecture/configuration entity referencing inaccessible evidence must not appear.
- A release baseline with any inaccessible source document must not appear.
- A hidden/unknown `focus_part` must return a generic not-found response.
- `Все зоны` must aggregate only areas already allowed for the caller.

## CPU acceptance

Run the normal CPU-only application profile with the LLM/VLM service disabled or unavailable. The Digital Thread endpoint and UI card must continue to work because the graph is deterministic SQL/in-memory processing.

## Regression gates

```bash
cd backend
PYTHONPATH=. pytest -q

cd ..
python scripts/api_access_preflight.py
python scripts/docker_security_preflight.py
python scripts/compose_security_preflight.py
python scripts/build_preflight.py
```

On an approved Docker build host:

```bash
docker compose build
make dockle
make acceptance
```

Do not report a Docker image-layer or Dockle pass unless those commands were actually executed on a host with the required runtime.

## Release authority

Passing this acceptance proves the Digital Thread Explorer behavior and access controls for the pilot. It does not constitute PLM/PDM release, financial approval, PPAP approval, homologation, functional-safety approval or SOP authorization.
