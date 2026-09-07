# Pilot Acceptance — Release Baseline & BOM Compare v4.9

Use one bounded automotive assembly with two known BOM revisions.

## BOM compare

- Load BOM A and BOM B for the same parent assembly.
- Include at least one added item, removed item, position replacement, quantity change and child-revision change.
- If available, include supplier and unit-price columns.
- Verify the UI reports each category separately and does not classify a same-position replacement as an ordinary add/remove pair.
- Confirm both source-document SHA-256 hashes and both BOM fingerprints are shown through the API.

## Design Freeze baseline

- Freeze a `design_freeze` baseline as an engineer.
- Confirm the snapshot contains source documents, BOM, requirements/V&V, PPAP/supplier state and ECR/ECO state.
- Modify the current engineering data after the freeze.
- Confirm the old baseline fingerprint/snapshot is unchanged.
- Freeze a second baseline and compare them.

## Vehicle variant

- Freeze a baseline for a configured vehicle variant.
- Leave one part applicability UNKNOWN.
- Confirm the baseline is created but `release_candidate=false` and the UNKNOWN is explicitly listed.

## Authorization

- Remove access to one source document used by the baseline.
- Confirm the user can no longer open or compare that baseline.
- Confirm Project access does not bypass Document ACL.

## Release/SOP authority

- Engineer user may create Design Freeze/Audit snapshots.
- Release/SOP baseline creation must require Engineering Admin.
- Even a clean baseline must show `human_release_approval_required=true`.
