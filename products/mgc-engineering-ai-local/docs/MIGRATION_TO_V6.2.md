# Migration to v6.2

v6.2 is additive and backward compatible at the API/schema level.

1. Back up v6.1.0 using the approved backup procedure.
2. Build v6.2 images on the approved build host.
3. Choose `DEPLOYMENT_PROFILE=core`, `ai` or `advanced`.
4. Run the one-shot schema migration / normal startup migration according to enterprise policy.
5. Verify `/api/v1/health/ready` and `/api/v1/runtime`.
6. Validate Object 360 for a representative Part, VIN, Change and Defect.
7. Re-run integration reconciliation and controlled-pilot gates.

### Compatibility

Legacy routes remain available when their feature is enabled. No v6.1 business table is deleted or renamed.

### Recommended first deployment

Use `ai` for the existing 15–30 engineer controlled pilot. Use `core` for minimal deterministic deployments or constrained infrastructure. Enable `advanced` only when a real need exists for graph projection/native advanced capabilities.
