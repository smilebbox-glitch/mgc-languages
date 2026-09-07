# Configuration & Release Assurance v5.5 — Pilot Acceptance

## Acceptance scenarios

1. **EBOM↔MBOM aligned** — import an MBOM matching the visible EBOM for a selected variant; status is `ALIGNED`.
2. **Revision mismatch** — change the MBOM child revision; buildability becomes `RED` with an EBOM↔MBOM blocker.
3. **UNKNOWN applicability** — remove explicit applicability for a visible part; the part stays UNKNOWN and is never silently included in the 100% configuration.
4. **Effectivity / AS-BUILT** — configure Rev D effectivity and import an AS-BUILT vehicle with Rev C; the mismatch is RED unless a linked approved/active deviation authorizes Rev C.
5. **Change cut-in** — create a cut-in with old stock but no disposition/logistics confirmation/approved PPAP; readiness is BLOCKED and all gaps are explicit.
6. **Supersession** — define old→new revision/part rules and verify interchangeability/retrofit/stock-use are displayed without executing inventory actions.
7. **Release package** — generate a package and verify its SHA-256 fingerprint and `human_release_approval_required=true`.
8. **Release drift** — freeze a baseline containing MBOM/effectivity, then change a controlled MBOM field. Drift must become `DRIFT`; a different capture timestamp alone must remain `MATCH`.
9. **Variant / Plant Matrix** — verify the matrix reports each accessible variant/plant independently and does not aggregate hidden areas.
10. **Cross-system consistency** — verify PLM/PDM↔ERP/MES mismatch is reported read-only.
11. **ACL fail-closed** — link an authority-shadow row to both visible and hidden evidence; the whole row must disappear for the unauthorized user.
12. **Ask Configuration** — query why a configuration cannot be handed over; answer must be deterministic, evidence-based, CPU-only and must not claim approval.
13. **Manufacturing Handover** — confirm the handover result always requires human approval even when evidence is GREEN.
14. **No source-system mutation** — verify no v5.5 endpoint writes to PLM/PDM, ERP, MES, warehouse or PLC/SCADA systems.

## Build-host gate

```bash
docker compose build
make dockle
make acceptance
```

Run the gate with representative corporate SSO identities, at least two manufacturing areas, two variants, one real EBOM/MBOM pair, PPAP evidence, one cut-in and an AS-BUILT sample.
