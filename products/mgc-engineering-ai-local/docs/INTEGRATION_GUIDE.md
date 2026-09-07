# Integration Guide

## Principle

MGC Engineering AI does not hard-code one PLM/ERP product into the knowledge core. Vendor systems are isolated behind connector contracts so upgrades or substitutions do not rewrite RAG/CAD/Part 360 logic.

## Preferred source patterns

### 1. Mounted engineering share
Recommended for SMB/NFS/file servers: mount the company share **read-only on the Docker host** and expose it to the API/worker as `/integrations/share:ro`.

Connector:

```json
{
  "code": "r-and-d-share",
  "name": "R&D Controlled Documents",
  "connector_type": "mounted_folder",
  "config": {
    "path": "/integrations/share",
    "extensions": [".pdf", ".xlsx", ".step", ".jt"]
  },
  "acl_groups": ["engineering-rd"]
}
```

This is preferable to embedding SMB credentials inside the application.

### 2. PLM/PDM/engineering REST gateway
The gateway list endpoint should return:

```json
{
  "items": [
    {
      "external_id": "PLM-123",
      "name": "8450012345_REV_D_drawing.pdf",
      "kind": "drawing",
      "part_number": "8450012345",
      "revision": "D",
      "project_code": "P123",
      "modified_at": "2026-09-04T08:10:00Z",
      "checksum": "optional-source-checksum",
      "download_url": "/api/assets/PLM-123/content"
    }
  ],
  "next_cursor": "opaque-next-cursor"
}
```

The connector supports field mapping when the gateway uses different names.

Example:

```json
{
  "base_url": "https://plm-gateway.internal",
  "list_path": "/engineering/assets",
  "items_key": "results",
  "next_cursor_key": "cursor",
  "field_map": {
    "external_id": "uid",
    "name": "fileName",
    "part_number": "itemId",
    "revision": "revId"
  }
}
```

Secrets:

```json
{"token_env":"PLM_API_TOKEN"}
```

OAuth2 client credentials can be configured without persisting the client secret:

```json
{
  "config": {
    "oauth_token_url": "https://idp.internal/oauth/token",
    "oauth_client_id": "mgc-engineering-ai",
    "oauth_scope": "plm.read"
  },
  "secrets": {
    "oauth_client_secret_env": "PLM_OAUTH_CLIENT_SECRET"
  }
}
```

For mTLS, reference file paths injected by the deployment secret/certificate mechanism:

```json
{
  "secrets": {
    "client_cert_env": "PLM_MTLS_CERT_PATH",
    "client_key_env": "PLM_MTLS_KEY_PATH"
  }
}
```

`ca_bundle` may be set in connector config to an internal CA bundle path.

### 3. ERP/BOM gateway
List endpoint:

```json
{
  "items": [
    {"id":"BOM-01","part_number":"ASM-100","revision":"B","modified_at":"..."}
  ],
  "next_cursor": null
}
```

Detail endpoint:

```json
{
  "items": [
    {"child_part_number":"8450012345","child_revision":"D","quantity":2,"description":"Bracket"}
  ]
}
```

The connector materializes this into CSV evidence, allowing the existing deterministic BOM parser to remain the source of truth.

## Idempotency

The sync engine skips an object when the source fingerprint has not changed. Preferred fingerprint order:
1. source-provided checksum;
2. source modification/version token;
3. locally calculated SHA-256 after download.

Downloaded bytes are stored immutably by digest. A changed external object creates a new document and an `ExternalObjectVersion` lineage entry.

## ACL

`acl_groups` belong to the integration system and are applied at document creation. Do not ingest a mixed-classification source through one broad group. Create separate connector registrations for separately controlled datasets.

## Push sync

For systems that can emit events, configure `webhook_secret_env` and POST a signed payload to:

```text
/api/v1/integrations/webhooks/<system-code>
```

The event does not directly mutate knowledge. It triggers a normal cursor-based synchronization, preserving idempotency and audit behavior.

## Vendor mapping

| Corporate source | Recommended adapter |
|---|---|
| SMB/NFS file server | host read-only mount + `mounted_folder` |
| Teamcenter / Windchill / 3DEXPERIENCE | thin internal gateway + `plm_rest`/`pdm_rest` |
| SAP/1C/other ERP BOM | thin internal BOM gateway + `bom_rest` |
| document management system | `engineering_rest` |
| КОМПАС-3D M3D/A3D/T3D/CDW/FRW/SPW/KDW | approved Windows KOMPAS SDK/Automation gateway + `cad_gateway` |
| T-FLEX CAD GRB | approved Windows T-FLEX Open API gateway + `cad_gateway` |
| CATIA/NX/Creo/JT/SOLIDWORKS | licensed converter sidecar + `cad_gateway` |

The exact vendor API, authentication scheme and object model must be mapped during the pilot discovery phase.
