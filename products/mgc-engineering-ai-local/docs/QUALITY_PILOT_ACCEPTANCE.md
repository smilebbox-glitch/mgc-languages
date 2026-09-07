# v4.1 Quality Pilot Acceptance

## People
Use at least:
- 1 Product/Process Engineer;
- 1 Manufacturing Engineer from the selected area;
- 1 Quality Engineer/SQE;
- 1 Engineering Admin.

## Acceptance scenario

1. Open an automotive project and select **Body/Welding** or **Assembly**.
2. Add an APQP deliverable with owner/due date and confirm it appears only in the relevant area plus project-wide views.
3. Create a safety or critical Special Characteristic linked to a visible part.
4. Confirm the system creates a gap for missing PFMEA and Control Plan.
5. Add a PFMEA row and link it to the characteristic.
6. Confirm only the Control Plan gap remains.
7. Add an active Control Plan row with a reaction plan and link it to the characteristic.
8. Confirm the Core Tools coverage gap closes.
9. Create a PPAP record, move it to `rejected`, confirm it appears as a critical blocker, then set it to the approved corporate state in a test scenario.
10. Create a high/critical 8D and confirm it affects the quality gate.
11. Attempt to close 8D without D1-D8: the API must reject closure.
12. Fill D1-D8 and close the test record; verify history/audit events.
13. Verify that a user without access to a source drawing cannot infer its Special Characteristic or evidence ID through the Quality workspace.
14. Change the project manufacturing area and confirm the same UI filters quality data without adding separate global pages.

## Pass criteria
- no cross-area/project/document ACL leakage;
- project quality gate explains each blocker;
- no automatic product release authority;
- no proprietary AIAG/VDA forms embedded;
- PFMEA internal risk band is visibly separate from customer-configured Action Priority;
- Docker/security gates stay green;
- Quality users judge the collapsed UI understandable without training on the backend data model.
