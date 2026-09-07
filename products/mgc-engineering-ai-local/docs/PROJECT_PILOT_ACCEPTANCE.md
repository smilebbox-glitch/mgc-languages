# Project Workspace Pilot Acceptance — v3.9.0

Use at least two engineering groups and one restricted document to validate both function and ACL behavior.

1. Engineering Admin creates project `PILOT-01`, configures root assembly and target date.
2. Upload at least one CAD model, drawing and BOM with `project_code=PILOT-01`.
3. Confirm the assembly tree follows the visible BOM and does not invent missing children.
4. Create milestones; set one overdue and unfinished. Confirm readiness becomes `needs_review` and the milestone appears as a blocker.
5. Create a critical validation issue. Confirm readiness becomes `blocked` and the quality gate decreases.
6. Create an urgent ECR/ECO. Confirm it appears in the project and contributes to the changes gate/blockers.
7. Resolve the issue/change and complete milestones. Confirm the score recomputes deterministically.
8. Verify the UI always states that release readiness is advisory and human approval is required.
9. Put one project document in a second ACL group. Login as an engineer who sees the project but not that document. Confirm the hidden document and its derived issue are absent from workspace output.
10. Login as a non-engineer and confirm Project Workspace routes are denied by the engineer-only gate.
