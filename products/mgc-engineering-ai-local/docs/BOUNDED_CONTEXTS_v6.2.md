# Bounded Contexts — v6.2

| Context | Primary ownership | Notes |
|---|---|---|
| Engineering Core | Project, Part, Document, Requirement, Drawing, CAD, Relationship | Base engineering identity and evidence relationships |
| Configuration & Change | BOM, revision, effectivity, ECR/ECO, release, impact | Configuration/release consistency |
| Manufacturing & Quality | Process, build, VIN, genealogy, PFMEA, Control Plan, defect, series quality | Plant/build/quality evidence |
| Supplier & Field | Supplier, PPAP, 8D, Run@Rate, warranty, field reliability | Optional advanced lifecycle context |
| Intelligence & Search | Search, RAG, memory, analytics, explanation | Enrichment; never authoritative for core facts |
| Platform & Operations | Auth, ACL, audit, evidence, actions, workflows, integrations, operations | Shared platform contracts |

## Dependency rule

A context may call Platform contracts and explicit context facades. New code should not create arbitrary imports between individual feature modules. Cross-context results should pass identifiers, EvidenceRefs and normalized Actions rather than ORM objects wherever practical.

## Why modular monolith

The current scale and team/deployment model benefit from one backend process, one auth boundary and local database transactions. Microservices would add distributed transactions, retries, service discovery and deployment/version coupling before there is evidence that those costs are necessary.
