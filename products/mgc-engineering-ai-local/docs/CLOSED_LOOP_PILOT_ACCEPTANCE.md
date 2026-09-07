# v5.3 Closed-Loop Pilot Acceptance

1. Create a Decision Record linked to a visible part/change and confirm inaccessible evidence is rejected.
2. Confirm a non-admin cannot place a Decision Record into controlled approved/verified/closed state.
3. Record post-change Production Feedback and verify defect-rate and planned-vs-actual calculations.
4. Confirm final effective/ineffective review requires Engineering Admin and is searchable by Engineering Knowledge Memory.
5. Create an expired deviation and confirm the API/UI reports `expired` without mutating historical approval data.
6. Confirm non-admin cannot approve/activate/close a controlled deviation.
7. Create a risk and verify deterministic initial/residual P×S×D scores; non-admin cannot accept/close the risk.
8. Run Risk-Based Validation Planner for material + supplier + geometry change and confirm human V&V approval flag remains true.
9. Run Root-Cause Explorer on a visible defect and confirm `causal_claim=false` plus explainable paths.
10. Link a defect to mixed visible/hidden evidence and confirm the defect/root-cause view fails closed.
11. Verify Supplier Quality Closed Loop uses only visible PPAP/incoming-quality/8D evidence.
12. Confirm Release Confidence is advisory and does not mutate Project Readiness or release baselines.
13. Confirm all human-facing API routes remain identity-protected and Project/Area/Document ACL rules are preserved.
14. On the approved build host run `docker compose build`, `make dockle`, and `make acceptance`.
