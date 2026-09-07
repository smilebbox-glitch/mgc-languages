# Engineering Program Control — Pilot Acceptance v5.4

## Functional acceptance

1. Create three visible milestones: preparation → Design Freeze → SOP.
2. Add finish-to-start dependencies with explicit lag days.
3. Confirm Program Control shows the next gate and an explainable dependency chain.
4. Attempt to create a dependency cycle and confirm the API rejects it.
5. Make one predecessor overdue and confirm gate forecast becomes RED with an explicit blocker reason.
6. Add a high/critical residual Engineering Risk and confirm it appears in top actions.
7. Add a passed V&V record with evidence and approved PPAP; confirm maturity reflects evidence state.
8. Run milestone slip simulation and confirm downstream dates change only in the response, not in stored milestones.
9. Filter to a manufacturing area and confirm unrelated/unauthorized area data is excluded.
10. Add mixed visible/hidden evidence to a risk or gate source and confirm the cross-domain object fails closed.

## Security / governance acceptance

- Every human Program Control API requires `get_identity`.
- Project/Manufacturing Area/Document ACL remains stronger than aggregation.
- Program dependencies cannot reveal inaccessible milestones.
- Program Control never writes PLC/MES/ERP/PLM state.
- Gate forecast never performs automatic approval.
- No probabilistic date prediction is claimed.

## Build-host acceptance

```bash
docker compose build
make dockle
make acceptance
```

The packaging environment may run static/preflight checks without Docker. Do not report an image build or Dockle layer scan unless those commands actually ran on the approved build host.
