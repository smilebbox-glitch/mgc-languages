# Real Integration Checklist

Use this checklist with IT, information security, PLM/PDM, ERP and CAD administrators before replacing the simulators.

## 1. Identity / SSO

Collect:
- OIDC issuer URL;
- client ID for MGC Engineering AI;
- approved redirect URL;
- audience expected in access tokens;
- username claim;
- group claim;
- engineering groups and owners;
- token lifetime;
- JWKS/discovery reachability from the application network;
- logout/session requirements.

Decide:
- which group receives `engineering-admin` equivalent;
- whether `all` ACL is permitted for any company data;
- how project-specific groups map to source repositories.

## 2. PLM / PDM

Record:
- product and version (e.g. Teamcenter/Windchill/3DEXPERIENCE/other);
- authoritative object IDs;
- part-number field;
- revision field;
- lifecycle/status field;
- project/program field;
- document classification/type field;
- checksum or stable version/change token;
- modified timestamp;
- file-content download method;
- pagination/delta checkpoint mechanism;
- deletion/obsolete/retired semantics;
- service account/API client authentication;
- whether webhooks/events exist.

Minimum pilot gateway contract:
- list changed/visible assets;
- return stable external ID + part/revision metadata;
- download original file bytes;
- optional checkpoint;
- read-only access.

## 3. ERP / BOM

Record:
- authoritative BOM source;
- parent part/revision;
- child part/revision;
- quantity and unit;
- effectivity/valid-from/valid-to if used;
- plant/site/program dimension;
- alternates/substitutes handling;
- phantom assemblies handling;
- source status/release state.

Start with one assembly that engineers can manually validate row by row.

## 4. Native CAD

Record:
- formats actually used: CATPart/CATProduct/NX PRT/Creo PRT/JT/SLDPRT/SLDASM/etc.;
- software versions generating those files;
- required PMI/GD&T/product-structure fidelity;
- approved server-side conversion SDK;
- license terms and license-server access;
- desired neutral target: STEP AP242 preferred where compatible;
- maximum typical assembly size/file size;
- expected conversion throughput;
- encrypted/password-protected CAD behavior.

Pilot acceptance set should contain at least:
- simple part;
- complex part;
- assembly;
- PMI/GD&T example;
- corrupted/unsupported file;
- two known revisions with verified changes.

## 5. File shares

For every share:
- UNC/NFS source path;
- host-side mount path;
- read-only service account;
- folder classification/ACL mapping;
- file extensions;
- expected file count/size;
- update cadence;
- retention/deletion policy.

Preferred deployment is infrastructure-managed read-only mount -> `mounted_folder`, not application-managed SMB credentials.

## 6. Network/security

Define allowed flows:

```text
User -> auth proxy/gateway
API/worker -> PostgreSQL/Qdrant/Redis/Neo4j/MinIO
API/worker -> PLM gateway
API/worker -> ERP/BOM gateway
API -> OIDC discovery/JWKS
API -> CAD Gateway
CAD Gateway -> license server (only if required)
```

Also define:
- TLS/mTLS requirements;
- internal CA bundle;
- proxy/no-proxy requirements;
- container registry policy;
- vulnerability scanning;
- log/SIEM destination;
- backup target;
- data residency requirements.

## 7. Pilot scope

Choose exactly one bounded scope first:
- one project/program;
- one engineering group;
- one PLM source;
- one BOM hierarchy;
- 100–5,000 representative documents/CAD assets;
- a golden question/review set authored by engineers.

Do not start by indexing the entire corporate engineering estate.

## 8. Acceptance metrics

Agree target values before testing:
- source synchronization success rate;
- duplicate/idempotency behavior;
- retrieval Recall@K/MRR;
- citation correctness;
- ACL leakage = zero in the test set;
- CAD conversion success rate by format;
- validated geometry agreement on reference parts;
- design-review finding precision/recall for selected rules;
- p50/p95 query latency;
- p50/p95 ingest/conversion latency;
- engineer review time saved.

## v6.0.2 contract / data-confidence gate

Before declaring a PLM/PDM/ERP/MES/QMS adapter pilot-ready, also complete `docs/INTEGRATION_HARDENING_PILOT_ACCEPTANCE.md`. In particular, verify source identity semantics, required-field contract, freshness SLA, immutable update history, payload-digest fallback, quarantine/replay and authoritative-source reconciliation.


## v6.0.3 reconciliation / controlled-pilot gate

Before pilot go-live, configure explicit reconciliation roles for the real sources and execute `POST /api/v1/integrations/reconciliation` for the bounded pilot project. Record and sign off:

- PLM EBOM ↔ ERP MBOM = `MATCH` for the golden scope;
- MES genealogy ↔ released configuration = `MATCH` for representative VINs;
- QMS Part/VIN/Supplier linkage coverage ≥ agreed threshold;
- mapping coverage ≥ agreed threshold and stale mappings = 0;
- freshness and recent sync success meet the agreed SLO;
- quarantine backlog = 0 for required sources;
- no unresolved source-of-truth conflicts;
- all aliases used by the pilot are human-confirmed and fingerprint-current.

Do not bulk-create inferred mappings merely to reach the coverage target. The gate is evidence for a controlled pilot only; corporate IT/Engineering/Quality owners still approve go-live.
