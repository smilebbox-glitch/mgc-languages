# Engineering Knowledge Memory — v5.2

## Purpose

v5.2 adds a reusable engineering-memory layer on top of the Digital Thread and Change Intelligence. It answers a different question from document RAG:

> Have we seen a materially similar engineering change, defect or problem before, what was done, and what evidence exists for the outcome?

The feature is advisory. Similarity never proves equal root cause and never auto-approves a design, process, supplier, ECR/ECO, PPAP, SOP or product release.

## Sources

The memory index is assembled from existing controlled engineering records:

- implemented/rejected/current ECR/ECO records;
- 8D problem-solving records;
- process defects;
- Design Reviews;
- deterministic Validation Issues;
- human-curated `EngineeringLesson` records.

The source record remains authoritative. A lesson is a reusable summary, not a replacement for the original evidence.

## Historical case vs validated lesson

A historical case can be shown as an analogue, but it is not automatically promoted to a recommendation.

`EngineeringLesson.status`:

- `draft` — engineer saved a historical case as a candidate lesson;
- `validated` — an Engineering Admin explicitly confirmed outcome/effectiveness;
- `archived` — retained but not offered as active reusable knowledge.

Validation requires an explicit outcome and effectiveness (`positive`, `mixed`, `negative`, or `verified`).

## Deterministic similarity

The CPU-only ranking uses explainable signals:

- lexical overlap between query/problem/decision/outcome/tags;
- exact part-number match;
- conservative part-family prefix signal;
- manufacturing-area match;
- validated-result bonus;
- validated Lessons Learned bonus.

Every result includes `why_similar`. No LLM is used to invent similarity relationships.

## Portfolio scope

The UI supports:

- `project` — current project only;
- `portfolio` — all projects already visible to the caller.

Portfolio scope does not grant access. Project ACL, Manufacturing Area ACL and Document ACL are applied before a case enters the memory set.

If any evidence document required by a case is hidden, that whole case fails closed. The same rule applies to curated lessons.

## Recurrence detection

Open defects/8D/changes/issues are compared with closed or reusable historical cases. A recurrence signal means only:

> a sufficiently similar historical pattern exists and should be checked.

It is not automatic root-cause identification.

## Ask Engineering Memory

The question endpoint returns a deterministic synthesis from ranked historical cases. It names the historical records, project, similarity and stored outcome. The core works without an LLM/GPU.

## Runtime and authority boundary

- CPU-only deterministic core;
- no online model/download requirement;
- no writes to PLM/PDM/ERP/MES/SCADA;
- no automatic ECO/PPAP/SOP/release decision;
- source evidence remains authoritative;
- human engineering judgement remains mandatory.
