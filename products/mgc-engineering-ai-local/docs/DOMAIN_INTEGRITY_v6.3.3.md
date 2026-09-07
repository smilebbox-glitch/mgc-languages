# MGC Engineering AI Local v6.3.3 — Database & Domain Integrity

## Purpose

v6.3.3 hardens collaborative engineering writes without introducing microservices or a second PLM/MES. PostgreSQL remains the authoritative engineering transaction boundary.

## Optimistic concurrency

The following human-edited controlled entities now carry an integer `row_version`:

- `ChangeRequest`;
- `ProcessStation`;
- `WorkInstruction`;
- `ManufacturingLayout`.

SQLAlchemy versioned updates prevent two concurrent database sessions from silently overwriting one another. UI/API update contracts also accept `expected_version` (or `expected_layout_version`) so a long-lived browser form can detect that another engineer saved a newer version after the form was opened.

A stale edit returns HTTP 409 with stable code `EDIT_CONFLICT`. The client must refresh the authoritative record and re-apply the intended change; the server never auto-merges engineering content.

## Unit of Work

Critical manufacturing-engineering writes now commit domain state and audit evidence in one transaction:

- Work Instruction create/import/update/translation/review;
- Process Station update;
- Manufacturing Layout creation and station placement.

ECR/ECO state transitions and their hash-chained `ChangeEvent` records are also committed atomically. A failure in event/audit persistence rolls back the corresponding domain write.

## Database invariants

Fresh schemas include CHECK constraints. v6.3.3 upgrades validate legacy rows before adding equivalent enforcement.

- BOM quantity must be greater than zero;
- station `headcount >= 1`;
- station `takt_time_sec` is null or non-negative;
- Work Instruction `cycle_time_sec` is null or non-negative;
- layout placement coordinates remain inside the validated engineering canvas bounds on fresh schemas.

For PostgreSQL, additive CHECK constraints are created when missing. For SQLite pilot databases, equivalent guard triggers are installed for core legacy invariants.

Migration is fail-closed: invalid legacy data is not silently changed. The DBA/engineering owner must repair the offending rows and rerun migration.

## Work Instruction collaboration

The UI retains the `row_version` returned with each Work Instruction. Edit, status, translation and translation-review actions send that version back to the API. A stale editor receives an explicit conflict instead of overwriting a colleague.

Approved Work Instructions remain immutable under the v6.3.1 governance rule; changes require a new revision or obsolescence transition.

## Layout collaboration

Manufacturing Layouts use a single layout `row_version` as the concurrency token for placement edits. Every placement mutation advances the layout revision token. Two engineers editing the same layout cannot silently overwrite station placement state.

## Change / ECR / ECO integrity

`ChangeRequest` now participates in optimistic concurrency. Decision, implementation and completion requests may carry `expected_version`. The internal change-event ledger is row-locked and updated in the same Unit of Work as the change state.

This does not replace formal PLM/ECR/ECO authority. MGC remains an engineering orchestration/evidence layer with explicit human approvals.

## Boundaries

v6.3.3 does not provide CRDT/automatic text merge, distributed transactions across external PLM/MES/QMS, or machine control. Conflicting engineering edits fail visibly and require human resolution.
