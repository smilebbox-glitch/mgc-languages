# Approval & Release Governance — v6.3.5

## Purpose
v6.3.5 adds a controlled engineering approval and production-handover layer without turning MGC into PLM/MES or a legal-signature system.

## Approval model
Approval policies can be scoped by `entity_type`, project and manufacturing area. A policy contains ordered stages. Supported stage eligibility is engineering user, Engineering Admin, or explicit identity groups. The policy snapshot is copied into each approval case so later policy edits cannot rewrite historical evidence.

Default policy when no configured policy exists:
1. Engineering Review — engineering user.
2. Final Release — Engineering Admin.

Maker-checker is enabled: an object author cannot approve their own object. With segregation of duties enabled, the same user cannot approve multiple stages of one approval cycle.

## Evidence integrity
Each approval cycle stores the SHA-256 of the submitted entity snapshot. Decisions are chained with `previous_hash` / `record_hash`. If the entity changes after submission, the approval cycle cannot continue and a new cycle is required.

These records are tamper-evident engineering approval evidence. They are **not** claimed to be a qualified electronic signature. A corporate PKI/e-sign adapter can be added later if required.

## Release Package
A Release Package is a controlled handover snapshot containing approved MGC-owned revisions and/or authoritative external evidence:
- Work Instruction;
- Manufacturing Layout;
- Engineering Change;
- Document/BOM evidence.

Package submission fails if WI/layout is not approved, the Engineering Change is not approved, or a document is not ready. Before release, every item is re-hashed. Any drift invalidates release and requires a new package/approval cycle.

## Authority boundaries
- PostgreSQL remains MGC source of truth for MGC-managed engineering records.
- PLM/PDM remains authority for product structure/BOM and external controlled documents.
- MES remains execution authority.
- Release Package creates a handover record only; it does not automatically write to PLM/PDM/MES/PLC/robot/torque equipment.

## Supersession
On successful Release Package release, older approved MGC Work Instruction/Layout revisions with the same business code are moved to `obsolete` and retain metadata identifying the superseding package/revision. External document/BOM evidence is never mutated.
