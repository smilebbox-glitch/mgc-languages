# Dependency Profiles — v6.2.2

| Profile | Python manifest | Adds | Optional packages intentionally absent below this profile |
|---|---|---|---|
| Core | `backend/requirements-core.txt` | deterministic platform/document/CAD/runtime stack | Qdrant, Sentence Transformers, Neo4j, MinIO |
| AI | `backend/requirements-ai.txt` | Qdrant + embeddings/reranker | Neo4j, MinIO |
| Advanced | `backend/requirements-advanced.txt` | Neo4j + MinIO | — |

`DEPLOYMENT_PROFILE` is used both by Docker build and runtime composition. The built image records the dependency envelope in `MGC_BUILD_PROFILE`. Runtime cannot select a wider profile than the image was built for.

Example:

```bash
# Minimal CPU/Core image and runtime
echo 'DEPLOYMENT_PROFILE=core' > .env
docker compose build
docker compose up -d

# AI dependency envelope; activate Compose AI services as required
echo 'DEPLOYMENT_PROFILE=ai' > .env
docker compose --profile ai build
docker compose --profile ai up -d
```

Profile composition does not grant authorization. ACL, document visibility, identity and human approval controls remain independent and stronger.
