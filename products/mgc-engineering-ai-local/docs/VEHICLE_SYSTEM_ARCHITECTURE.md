# Vehicle / System Architecture & Interface Management — v4.7

## Purpose

Model the automotive product as an explainable hierarchy and control interfaces between systems/components without replacing PLM/PDM.

## Hierarchy

`Vehicle → System → Subsystem → Assembly → Component`. A component may point to an existing part number. Nodes may be scoped to a manufacturing area and may carry evidence documents.

## Interface Matrix

Each interface records source and target node, interface type, criticality, linked requirements, ECR/ECO, specification data and evidence. Supported interface types: mechanical, electrical, fluid/gas, thermal, data, control and packaging/space.

## Verification rule

A user-visible PASSED status is not sufficient. Effective verification requires accessible evidence or a valid linked requirement verification. A fingerprint of the interface and both endpoints is stored at verification time. If the interface, linked requirements or an endpoint node changes, the old verification becomes stale and must be reviewed again.

## Impact analysis

For a selected part the service can return:
- architecture nodes that represent the part;
- connected interfaces and adjacent systems/components;
- linked requirement IDs;
- open ECR/ECO linked to those interfaces;
- related cost-line and supplier/localization records.

This is an advisory engineering impact map, not an automatic change approval.

## Security

The layer uses the existing Engineer-Only SSO + Project ACL + Manufacturing Area ACL + Document ACL chain. Hidden parts/evidence are not promoted by project or architecture access.

## UX principle

No new main-menu page is added. Architecture appears as one collapsible card in the Project Workspace. In collapsed form only node/interface counts, verified count and at most three gaps are visible.
