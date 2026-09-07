# Engineering Knowledge Memory — Pilot Acceptance v5.2

## P0 functional acceptance

1. Seed an implemented ECR/ECO with an explicit verification result and searchable problem/decision text.
2. Search Engineering Knowledge Memory with related engineering language and confirm the case is returned with a deterministic similarity score and `why_similar` reasons.
3. Seed a closed 8D with D5/D6/D7 content and verify the corrective action/outcome are visible.
4. Create a new open defect with similar wording and confirm a recurrence signal points to prior history without claiming identical root cause.
5. Promote one historical case to Lessons Learned. Confirm the first state is `draft`.
6. Confirm a draft lesson is not treated as a validated lesson.
7. As Engineering Admin, validate a lesson only after explicit outcome and effectiveness are present.
8. Confirm portfolio scope returns cases only from projects already accessible to the caller.

## Security acceptance

1. Add a historical case with one visible evidence document and one hidden evidence document.
2. Confirm the entire case disappears for a user who cannot see the hidden evidence.
3. Confirm the same fail-closed behavior for `EngineeringLesson`.
4. Confirm selecting portfolio scope does not reveal inaccessible project codes, part numbers, titles, outcomes or counts derived from hidden cases.
5. Confirm all human-facing v5.2 routes require engineer identity.

## Governance acceptance

Confirm the UI states that:

- historical similarity is not root-cause proof;
- a historical case is not automatically a recommendation;
- only human-validated lessons are marked `VALIDATED`;
- validated lessons remain advisory;
- PLM/PDM/ERP/MES/SCADA and formal approval workflows retain their authority.

## Runtime acceptance

Run the memory search and recurrence detector on the CPU profile with the generative model disabled. Core results must remain available.
