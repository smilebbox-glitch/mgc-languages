# Automotive Quality & Industrialization — v4.1

## Purpose

v4.1 adds an automotive quality layer to the existing Engineering Project Workspace without creating a second application or a dense quality dashboard.

The quality layer is **project-aware**, **manufacturing-area-aware**, **document-ACL-aware** and **engineer-only**. A welding engineer can work in the Body/Welding context; a Paint or Assembly user sees the same simple project UI with area-scoped quality data.

## Standards alignment

The implementation is designed as an open data/workflow model aligned with the current automotive Core Tools landscape:

- AIAG APQP 3rd Edition (published March 2024): project quality planning, gated management, change/risk focus.
- AIAG Control Plan 1st Edition (published March 2024): standalone Control Plan workflow, including Safe Launch phase support.
- AIAG/VDA FMEA Handbook: PFMEA data model for process risks.
- AIAG PPAP 4th Edition: production-part approval evidence/submission workflow.
- 8D / effective problem solving: structured D1-D8 problem-solving record and link to engineering change.

**Important:** this repository does not embed, reproduce or claim to replace proprietary AIAG/VDA forms, Action Priority tables, rating tables or customer-specific requirements. Corporate Quality owns those licensed methods and CSR rules. The platform stores links, evidence, statuses and user-entered ratings.

Official references:
- https://www.aiag.org/training-and-resources/manuals/details/APQP-3
- https://www.aiag.org/training-and-resources/manuals/details/CP-1
- https://www.aiag.org/training-and-resources/manuals/details/FMEAAV-1
- https://www.aiag.org/training-and-resources/manuals/details/PPAP-4
- https://www.aiag.org/training-and-resources/manuals/details/CQI-20

## Compact user experience

The primary navigation is unchanged. Quality is shown **inside the selected project**, not as six new global pages.

Collapsed state:

```text
КАЧЕСТВО И ИНДУСТРИАЛИЗАЦИЯ                84%
APQP 90% | Core Tools 75% | PPAP 100% | 8D 80%

2 пункта требуют внимания
! SC-07: нет активного Control Plan
△ PFMEA: высокий незакрытый риск — Missing weld

[ Открыть инструменты качества ]
```

Only after the engineer opens the quality tools are the internal tabs shown:

```text
APQP | Характеристики | PFMEA | Control Plan | PPAP | 8D
```

## Digital quality thread

```text
Requirement / Drawing / CAD
          |
          v
Special Characteristic
     |             |
     v             v
   PFMEA ------> Control Plan
                    |
                    v
              Safe Launch / Production
                    |
                    v
                   PPAP
                    |
       complaint / nonconformance
                    v
                    8D
                    |
             corrective change
                    v
                 ECR/ECO
```

The service flags missing links instead of silently assuming they exist.

## APQP

`APQPDeliverable` stores project/area deliverables with:
- project and manufacturing area;
- phase;
- owner;
- due date;
- status;
- linked part numbers;
- evidence document IDs;
- notes.

Statuses: `planned`, `in_progress`, `blocked`, `done`, `waived`.

The platform does not hard-code proprietary APQP forms. It provides a project gate and evidence-traceable deliverable register.

## Special Characteristics

`SpecialCharacteristic` can be linked to:
- project;
- manufacturing area;
- part/revision;
- source drawing/document and source coordinates/metadata;
- PFMEA items;
- Control Plan items.

Supported generic categories: safety, regulatory, critical, significant, customer, other. Symbols are user/customer configured.

Safety/regulatory characteristics without PFMEA or active Control Plan generate a **critical** quality gap. Other characteristics generate a warning.

## PFMEA

PFMEA records include:
- process step;
- function;
- failure mode;
- effect;
- cause;
- prevention control;
- detection control;
- S/O/D ratings entered by the organization;
- optional user/customer-configured Action Priority (`H/M/L`);
- recommended action, owner and due date;
- links to Special Characteristics and evidence.

The platform computes a separate `internal_risk_band` only for navigation and prioritization. It is explicitly **not** an AIAG/VDA Action Priority calculation and never overwrites the user/customer AP field.

## Control Plan

Control Plan records include:
- process step;
- controlled characteristic;
- optional Special Characteristic link;
- specification;
- measurement/control method;
- sample size;
- frequency;
- reaction plan;
- owner/status;
- control phase: prototype, pre-launch, production, safe-launch;
- evidence documents.

An active Control Plan item without a reaction plan becomes a visible gap.

## PPAP

PPAP is implemented as an evidence/submission workflow, not as a copyrighted checklist embedded in source code.

Fields include:
- part/revision;
- supplier/customer;
- organization-defined submission level;
- due/submitted/approved dates;
- status;
- `element_status_json` for customer-configured element names/statuses;
- evidence documents.

An explicitly rejected PPAP is a critical project blocker.

## 8D

The 8D record stores:
- complaint reference;
- affected part and manufacturing area;
- owner/team;
- severity/status;
- D1-D8 discipline content;
- evidence documents;
- optional link to ECR/ECO.

The service will not close an 8D unless D1-D8 all contain content. High/critical open 8D records affect project quality readiness. Lack of D7 prevention evidence / change linkage is shown as an advisory gap during verification/closure.

## Project readiness integration

The old quality gate (validation issues only) has been upgraded.

```text
Project Quality Gate =
45% deterministic validation/issue state
55% automotive Core Tools quality score
```

The Core Tools score is itself advisory:

```text
25% APQP
45% Special Characteristic ↔ PFMEA ↔ Control Plan coverage
20% PPAP
10% problem solving / 8D
```

These weights are pilot defaults, not an OEM standard. They should be configured by the company's Quality organization before production rollout.

No numeric score can release a product automatically. `human_release_approval_required=true` remains mandatory.

## ACL and confidentiality

Project access does not elevate document access.

Quality records with a part number are returned only when that part is visible through project evidence available to the user. Evidence document IDs are filtered by document ACL. A Special Characteristic based on a hidden source document is not surfaced to an unauthorized user.

## Recommended automotive pilot

Start with one project and 1-2 manufacturing areas, e.g. Body/Welding + Assembly:

1. Select 5-20 parts with known Special Characteristics.
2. Enter a small PFMEA set already approved by Quality.
3. Link 5-10 Control Plan items.
4. Create one APQP launch deliverable list.
5. Track one PPAP package.
6. Run one existing 8D through the system.
7. Verify all source-document ACL boundaries.
8. Compare system gaps with an expert's manual review.

Do not import the entire plant quality estate as the first pilot.
