# Corporate Deployment Architecture — v6.1.0

## Purpose
Reference architecture for a controlled automotive pilot with 15–30 engineers. It is a starting topology, not a performance certification. Final sizing must use the v6.0.4 target-host benchmark.

## Recommended pilot topology

```text
Corporate users -> TLS Enterprise Edge -> OIDC/Auth Proxy -> Gateway/API
                                                     |-> Workers/Beat
                                                     |-> PostgreSQL
                                                     |-> Qdrant / Redis
                                                     |-> local model server
                                                     |-> optional Neo4j / MinIO

PLM/PDM/ERP/MES/QMS -> approved read-only gateways -> MGC integration fabric
Backup target <- checksum-verified backup/restore process
```

Only 443 and, when machine webhooks are used, 9443 are intended for host ingress. Database/vector/queue/model ports stay on the internal network.

## Sizing policy
Use `POST /api/v1/deployment/plan` or `deployment/corporate-pilot/deployment-profile.example.yml`. The returned CPU/RAM/storage values are conservative reference starts. `certification_required=true` is invariant.

## Authority boundaries
MGC remains read-only toward authoritative PLM/ERP/MES/QMS integrations unless a separately approved connector is explicitly designed. Deployment planning never grants production authorization.
