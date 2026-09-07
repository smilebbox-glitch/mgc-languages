# Configuration & Release Assurance — v5.5

## Purpose

v5.5 closes the engineering-to-manufacturing configuration gap without replacing PLM/PDM, ERP or MES. It answers: **is this exact vehicle/assembly configuration consistently defined, planned and evidenced for manufacturing handover?**

## Data authority boundary

- **PLM/PDM** remains authoritative for EBOM/product definition.
- **ERP / manufacturing planning** remains authoritative for MBOM/material planning.
- **MES or approved import** remains authoritative for AS-BUILT observations.
- MGC stores ACL-controlled shadow/evidence rows to reconcile and explain differences. It does not write back to those source systems automatically.

## Main chain

```text
150% product definition
       ↓ variant applicability
100% exact configuration
       ↓
EBOM ↔ MBOM reconciliation
       ↓
Effectivity / Change Cut-In
       ↓
Buildability / Handover
       ↓
Release Package / Baseline
       ↓
AS-BUILT observation
       ↓
Release / system drift
```

## EBOM ↔ MBOM reconciliation

The comparison is deterministic and reports missing/extra rows plus child part, revision, quantity, unit and supplier differences. If no MBOM evidence exists, status is `NOT_CONFIGURED`, never `ALIGNED`.

## 150% → 100% configuration

Existing `ConfigurationApplicability` records resolve included/excluded parts for one `VehicleVariant`. Unresolved visible parts remain `UNKNOWN`; they are never silently included. A configuration is `exact_100_percent=true` only when applicability is explicitly resolved for the visible scope.

## Effectivity

Effectivity can be scoped by variant, plant, supplier, VIN range, serial range and effective date window. AS-BUILT assurance only accepts rules whose scope can be proven for the observed vehicle. A scoped rule with missing required context fails closed as unresolved.

## Change Cut-In

Cut-in readiness checks the explicit cut-in point (date/VIN), old-stock disposition, logistics cutover confirmation and approved PPAP for the target revision/supplier scope. It is evidence for engineering review; it does not execute stock or VIN transactions.

## AS-DESIGNED / AS-PLANNED / AS-BUILT

- AS-DESIGNED: visible released engineering structure/EBOM.
- AS-PLANNED: imported/configured MBOM.
- AS-BUILT: imported production observation.

A revision mismatch is `RED` unless a visible approved/active engineering deviation is linked; then it is surfaced as `AMBER`, not silently accepted as the released state.

## Buildability and Manufacturing Handover

Buildability aggregates configuration completeness, EBOM↔MBOM alignment, visible process/Work Instruction evidence, supplier/PPAP evidence and cut-in readiness. The result is `GREEN`, `AMBER` or `RED`, with explicit blockers/review items. Human release approval is always required.

## Release Package and drift

`mgc-configuration-release-package-v2` fingerprints a composite engineering + configuration assurance snapshot. Release Baseline schema `mgc-release-baseline-v3` additionally freezes manufacturing BOM, effectivity, cut-in and supersession data. Later changes therefore appear as Release Drift instead of being hidden by a matching EBOM alone.

## Supersession / stock-use rules

The system can record traceable replacement chains and explicit flags for interchangeability, retrofit and old-stock use. These are review evidence only; ERP/QMS/Engineering approval processes remain authoritative.

## Security

Project, Manufacturing Area, Part and Document ACL are applied before any cross-domain reconciliation. Evidence-bearing rows with mixed visible/hidden documents fail closed as a whole. Configuration-authority shadow writes through the human API require Engineering Admin.
