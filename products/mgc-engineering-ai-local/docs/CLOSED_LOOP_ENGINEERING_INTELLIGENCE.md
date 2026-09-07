# Closed-Loop Engineering Intelligence — v5.3

## Purpose
v5.3 closes the engineering feedback loop from a human engineering decision through implementation, production/quality observation, effectiveness review and reusable Engineering Memory.

```text
Requirement / Problem
        ↓
Engineering Decision
        ↓
ECR / ECO
        ↓
Design / BOM / Process / Supplier
        ↓
Validation / Release
        ↓
Production & Quality Feedback
        ↓
Effectiveness Review
        ↓
Lessons Learned / next decision
```

## Authority boundary
The module is an engineering intelligence/evidence layer. It does not replace PLM/PDM, ERP, QMS, MES or SCADA and does not send machine-control commands. Root-cause results are investigation candidates, not causal determinations. Release, deviation approval, risk acceptance and final effectiveness remain human-controlled.

## Engineering Decision Record
A Decision Record captures the problem, alternatives, selected option, rationale, expected outcome, linked part/change/evidence, accepted-risk level and later effectiveness. `approved`, `verified` and `closed` are controlled states.

## Production Feedback
Production Feedback records summarized post-change observations such as built population, defect quantity/rate and optional planned-vs-actual cost, mass and cycle-time deltas. It is evidence imported from or reconciled with authoritative systems, not a replacement for them.

## Change Effectiveness
A review links an implemented change, optional Decision Record and optional Production Feedback to a target and observed result. Final `effective` / `ineffective` assessment is human-confirmed. Finalized effectiveness becomes searchable historical evidence in Engineering Knowledge Memory.

## Deviation / Waiver
Deviation records are time- and/or quantity-bounded evidence for temporary departures from released configuration. Expiry is calculated explicitly. Approval does not execute a shop-floor disposition; authoritative production/QMS processes remain required.

## Engineering Risk Register
Risk uses explicit 1–5 Probability × Severity × Detectability values. Initial and residual scores are deterministic. Mitigations and evidence are traceable. Residual risk acceptance remains human-owned.

## Defect Root-Cause Explorer
The explorer connects a visible defect to candidate investigation paths such as recent changes, explicit 8D links, repeated defects on the same operation and supplier incoming-quality signals. It always returns `causal_claim=false`.

## Supplier Quality Closed Loop
Supplier view combines visible localization records, PPAP state, incoming inspection statistics and related 8D signals. Cross-domain rows fail closed when linked evidence is unavailable to the viewer.

## Risk-Based Validation Planner
The planner maps explicit what-if fields (material, thickness, geometry, supplier, revision) to deterministic `REQUIRED`, `REVIEW` and candidate-not-impacted verification scopes. It is advisory; the responsible engineer approves the actual V&V scope.

## Release Confidence / Early Signals
Release Confidence exposes separate Product, V&V, Supplier, Quality, Risk and Configuration signals instead of hiding them behind one opaque score. It does not alter existing Project/Release Readiness or grant release authority.

## CPU-first
All v5.3 deterministic functions run without LLM/VLM or GPU. Local AI may explain already-visible evidence, but is not required for the closed-loop core.
