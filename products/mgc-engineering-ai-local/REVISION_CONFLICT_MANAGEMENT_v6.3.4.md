# Engineering Revision & Conflict Management — v6.3.4

## Purpose

v6.3.4 adds controlled multi-user revision behavior on top of the v6.3.3 optimistic-locking and Unit-of-Work foundation. PostgreSQL remains authoritative. A stale client never overwrites a newer engineering record silently.

## Conflict contract

A stale write returns HTTP `409 EDIT_CONFLICT` with `expected_version`, `current_version` and a serialized `current_record`. The UI compares the authoritative server state with the engineer's unsaved payload. `auto_merge=false` is an invariant.

Controlled safety, quality, tooling, process-step and approval content is never merged by AI/CRDT automatically. The engineer refreshes the record and applies intended changes explicitly.

## Controlled revisions

### Work Instructions

Approved/obsolete WI revisions are immutable. A new revision:

- receives a new record ID and requested business revision;
- starts as `draft`;
- records lineage to the source revision;
- retains source/evidence links and controlled work content;
- does not inherit approval;
- for foreign-language sources, translation state becomes `stale` and translated content must be generated/reviewed again before approval.

### Manufacturing Layouts

A new layout revision starts as `draft`, records lineage and clones current station placements. The source layout remains unchanged.

## Revision snapshots

`engineering_revision_snapshots` stores a canonical JSON snapshot and SHA-256 digest keyed by entity/type/row version. Snapshots support forensic comparison and controlled revision lineage; they do not replace the primary domain tables.

## Write idempotency

`write_idempotency_records` stores `(user, route, idempotency key, request hash, response)` for selected mutation APIs. Replaying the same key with the same payload returns the recorded logical result. Reusing a key with a different payload fails closed.

This provides retry safety, not distributed exactly-once network delivery.

## Duplicate approvals

A Change Approval stage is unique per `(change_id, stage)`. The v6.3.4 migration checks existing data first and stops if duplicate legacy approval-stage rows exist; it never guesses which approval should survive.

## Administration / observability

Engineering Admin can inspect:

- `/api/v1/operations/integrity` — revision snapshots, write receipts, conflicts, duplicate approval status, stale WI translations;
- `/api/v1/operations/conflicts` — recent edit-conflict events without exposing unrestricted full record snapshots.

## Compatibility

- Application: `6.3.4`
- Schema: `6.3.4`
- v6.2.0 legacy API method/path contracts: `181/181` preserved
- Bounded-context API routes: `198`
- automatic merge: disabled
- human conflict resolution: required
