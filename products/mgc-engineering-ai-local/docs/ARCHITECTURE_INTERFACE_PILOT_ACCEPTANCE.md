# v4.7 Pilot Acceptance — Vehicle Architecture & Interfaces

Use one bounded automotive project with at least two connected systems and one real interface.

1. Create Vehicle → System → Component nodes and link real part numbers.
2. Create a critical mechanical interface without a requirement: confirm a critical blocker appears.
3. Link an OEM/internal requirement and create verification.
4. Attempt PASSED without evidence: confirm it is not considered effectively verified (API create path rejects this).
5. Add evidence or a valid requirement verification and confirm effective verification.
6. Change one interface endpoint/node: confirm previous verification becomes stale.
7. Run part impact analysis and confirm adjacent nodes/interfaces and linked ECR/ECO are shown.
8. Add cost/localization records for the part and confirm impact references them without exposing financial or supplier data outside ACL.
9. Cross-area ACL test: an engineer without Paint-area/document access must not see hidden Paint architecture nodes/interfaces in All Areas.
10. Confirm architecture readiness remains advisory and final release remains human-controlled.
