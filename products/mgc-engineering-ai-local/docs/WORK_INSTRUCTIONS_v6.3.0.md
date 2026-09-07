# Manufacturing Work Instructions & Station Intelligence — v6.3.0

## User model

The default engineering flow is **manufacturing area → line → station → operation → work instruction**. There is no cross-shop instruction pool in the normal UI. Assembly, body/welding, paint, stamping, components, logistics and other configured areas remain separate and inherit the existing Project / Manufacturing Area / Document ACL.

## Work instruction record

A Work Instruction stores code/revision/status, source language/factory/document, station and optional operation, explicit steps, safety and quality checkpoints, tools/fixtures, PPE, required skill, operator role, cycle time and evidence. Status is `draft → in_review → approved → obsolete`; final approval is human-controlled.

Partner instructions can be uploaded as PDF/DOCX/PPTX/TXT/MD. Local parsing creates a draft; it does not infer missing technical requirements. The foreign source remains available beside a separately stored Russian working translation.

## Station and layout

Stations can be added under a manufacturing line with operator role, headcount, work content and takt time. Layouts can be created blank or linked to an uploaded PDF/image/CAD-layout source. Engineers place station cards on the layout using normalized coordinates; each card exposes station code/name, role/headcount and instruction coverage.

The layout is an engineering information surface, not shop-floor machine control. It does not issue commands to PLCs, robots, conveyors, torque controllers or paint equipment.

## AI / RAG

Instruction Q&A first filters by project, exact manufacturing area and existing document ACL; station/operation filters narrow it further. Core profile returns deterministic relevant instruction evidence. AI profiles may synthesize a local answer from the same filtered evidence. The prompt explicitly forbids invention of torque, dimensions, PPE/tools, safety/quality requirements or approvals.

## Governance

- foreign WI cannot be approved until its Russian translation has human review status;
- source document visibility is fail-closed;
- approved WI requires an explicit station and explicit steps;
- translation/review/status changes are audited;
- source text and source BOM values remain immutable views/evidence.
