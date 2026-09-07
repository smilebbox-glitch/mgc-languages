# MGC Engineering AI Local v4.9.0

## Engineering Traceability & Release Baseline

- Immutable Design Freeze / Release / SOP / Audit baselines with SHA-256 fingerprint.
- Optional freeze by Vehicle Variant.
- Snapshot of documents + hashes, part revisions, BOM, requirements/V&V, PPAP, suppliers, Design Review and ECR/ECO.
- UNKNOWN vehicle applicability is never silently treated as released applicability.
- Release/SOP freeze requires Engineering Admin; final human release approval always remains mandatory.
- Baselines fail closed if the viewer cannot access every source document that contributed to the snapshot.

## BOM Version Compare

- Compare any two BOM source-document versions for one assembly.
- Added / removed / replaced-at-position / moved / changed lines are separated.
- Revision, quantity, unit, description, supplier and unit-price differences are supported.
- If both BOMs have complete prices in one currency, the UI shows a deterministic BOM cost delta; incomplete pricing never produces a misleading total.
- BOM rows now optionally store position, supplier code/name, unit cost and currency.
- Deterministic diff only; no LLM is used to invent or infer structure changes.

## UI

- No new global navigation item.
- One compact `Релиз и версии BOM` card inside Project Workspace.
- One `Сравнить версии BOM` card inside Part 360.
- Detailed diff is hidden until the user explicitly compares versions.
