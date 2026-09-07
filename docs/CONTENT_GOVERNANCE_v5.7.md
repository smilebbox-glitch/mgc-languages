# Content Governance v5.7

Lifecycle: `draft -> review -> published -> archived`.

- Editor may author and submit content.
- With `TERM_APPROVAL_REQUIRED=true`, Editor cannot publish directly.
- Admin approves/rejects and may rollback to an earlier revision.
- Every revision stores a full snapshot and actor.
- Source provenance is explicit: company standard, supplier, work instruction, engineering document, language expert, public dictionary, AI suggestion, import/manual.
- AI-suggested terminology must never be auto-published in controlled pilot mode.

Endpoints: revisions, submit-review, approve, reject, rollback are under `/api/admin/terms/{id}/...`.
