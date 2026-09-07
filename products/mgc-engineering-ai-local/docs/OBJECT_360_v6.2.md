# Object 360 — v6.2

Object 360 is the primary read-only navigation surface for engineering context.

Supported initial object types:

- part;
- VIN/build;
- change/ECO;
- defect;
- requirement;
- supplier.

Endpoint:

`GET /api/v1/objects/{object_type}/{object_id}`

Every response uses the same top-level structure:

- `identity`;
- `summary`;
- `sections`;
- `actions`;
- `evidence`;
- `governance`.

## Security rule

Object 360 never widens ACL. If a derived object depends on a mixed visible/hidden evidence set, the hidden evidence is not promoted. Sensitive cross-document results remain fail-closed.

## UX rule

The top navigation is reduced to Today, Projects, Object 360, Changes and Search/AI. Legacy Parts/Documents/Checks views remain available through drill-down and existing actions so v6.2 preserves capability while reducing permanent navigation load.
