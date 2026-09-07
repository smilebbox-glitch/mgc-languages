# UX Simplification & Pilot Feedback Closure — v6.0.7

## Goal

Reduce cognitive load without hiding engineering evidence or weakening approval/ACL boundaries. The first Project Workspace view is action-first: attention, explicit decisions and guided workflows. Specialist modules remain available through a single collapsed drill-down.

## Default information budget

- primary actions: maximum 5;
- human decisions: maximum 3;
- guided workflows: maximum 3;
- full domain cockpit and specialist modules: collapsed by default.

This is progressive disclosure, not data removal. All accessible evidence remains reachable.

## Pilot usability issue lifecycle

`OPEN -> ACCEPTED -> FIXED -> VERIFIED/CLOSED`

A usability issue contains role/surface/category/severity, a workflow-level problem statement, aggregate occurrence count, remediation and verification evidence. It must not contain participant identity, IP, raw query text, VIN/document viewing history or individual productivity metrics.

Closing as VERIFIED/CLOSED requires both remediation and verification evidence.

## Controlled pilot gate

- unresolved CRITICAL usability issue -> NO_GO;
- unresolved HIGH usability issue -> at best CONDITIONAL_GO;
- MEDIUM/INFO items remain visible as improvement backlog;
- a verified/closed issue is no longer an open gate.

The final deployment decision remains human and outside MGC.
