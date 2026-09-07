# Engineering Intelligence Operating System — v6.0

## Purpose

v6.0 consolidates MGC Engineering AI Local into one evidence-first operating layer. The existing v5.x services remain domain engines; Engineering OS summarizes their accessible state for a chosen work role and coordinates cross-domain cases.

## Role Cockpit

Supported focus profiles:

- Engineering
- Manufacturing Engineering
- Quality
- Supplier / Localization
- Program / Launch
- Field Reliability
- Engineering Leadership
- Engineering Admin

A role changes **presentation and prioritization only**. It is never authorization. Project, Manufacturing Area and Document ACL are evaluated first, and every Cockpit view is built from that already-filtered context.

## Unified Action Inbox

The inbox is derived, not manually copied, from controlled records such as:

- stale/missing engineering evidence and Digital Thread gaps;
- open high-risk ECR/ECO;
- Program Control blockers and due dates;
- residual risks, ineffective changes and expired deviations;
- configuration/manufacturing handover blockers;
- Pilot/Safe Launch recurrence and exit-review candidates;
- series capability/quality signals;
- DFMEA/V&V field gaps and campaign-review candidates;
- active cross-domain workflow cases.

Priority is deterministic from severity plus due-date urgency. The system does not autonomously approve, close or release engineering work.

## Decision Queue

A subset of the inbox is explicitly marked `decision_required=true` when a controlled human review is needed, for example release/handover blockers, residual risk, Safe Launch exit, DFMEA/V&V field gaps, campaign assessment or a workflow ready for closure.

## Cross-domain workflow cases

Supported templates:

```text
change_to_release
impact → technical review → V&V → configuration → human release review

defect_to_change
containment → root cause → 8D → ECR/ECO → effectiveness

field_to_change
field triage → exposure → DFMEA/V&V → engineering change → field effectiveness

launch_blocker
triage → owner action → evidence refresh → human gate review

supplier_issue
incoming quality → supplier 8D → PPAP → Run@Rate/capacity → human release review
```

Stage completion is explicit and auditable. Final workflow closure/cancellation through the API requires Engineering Admin. Workflow cases do not replace corporate project/task systems.

## ACL invariant

A workflow with mixed visible/hidden evidence fails closed for a viewer. A trigger/source-linked workflow must have visible evidence. Choosing another role does not reveal hidden records.

## System boundary

Engineering OS is not a PLM/PDM, ERP, MES, QMS, DMS, warranty system or project-management system of record. It is an Engineering Intelligence & Evidence layer and does not issue PLC/machine commands or automatic engineering approvals.
