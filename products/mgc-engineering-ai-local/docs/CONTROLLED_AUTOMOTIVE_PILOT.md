# Controlled Automotive Pilot — v6.0.6

## Purpose
Validate MGC Engineering AI Local with real automotive engineering workflows before production adoption. The pilot measures system/workflow outcomes, not employee performance.

## Required roles
- R&D / product engineering
- Manufacturing Engineering
- Quality Engineering

Supplier/Program/Field roles may be added, but cannot replace the three required roles.

## Required scenario families
1. Engineering change impact and evidence trace.
2. BOM/configuration comparison.
3. Manufacturing buildability / cut-in or process impact.
4. Defect investigation using VIN/part/supplier evidence.
5. Containment / suspect population or equivalent quality workflow.

## Privacy rule
Pilot telemetry stores only role/surface aggregate counts: sessions, completions, errors and total duration. Do not store user ID, employee ID, email, IP, raw query text, VIN history, document history or per-person productivity scores.

## Synthetic vs controlled
`synthetic` pilots validate the UAT harness and may only result in `PRECHECK_PASS/PRECHECK_FAIL`. Synthetic data can never authorize GO.

`controlled` pilots use real approved corporate data and require reconciliation, security and external runtime evidence before GO can be considered.

## Human authority
MGC outputs `GO`, `CONDITIONAL_GO` or `NO_GO` as an evidence summary. `human_go_live_required=true` is invariant. The corporate pilot owner, IT/Security and engineering leadership make the actual deployment decision.
