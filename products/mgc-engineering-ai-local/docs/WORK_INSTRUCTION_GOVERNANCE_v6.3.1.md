# Work Instruction Governance Hardening — v6.3.1

## Approved revision immutability

An approved Work Instruction revision cannot be edited in place. The only allowed direct lifecycle transition is to `obsolete`. Engineering content changes require creation of a new revision.

This prevents a record that was reviewed/approved for one content state from silently changing while retaining the same approval status.

## Translation fingerprint

For non-Russian instructions, the reviewed Russian translation is tied to a SHA-256 fingerprint generated from:

- original source text;
- ordered instruction steps;
- step title/text;
- step safety note;
- step quality note.

The fingerprint is stored with translation metadata.

If source content changes after translation/review:

1. fingerprint comparison fails;
2. translation status becomes `stale`;
3. the previous Russian text is retained only as traceable historical working content;
4. approval is blocked;
5. engineer must translate again;
6. Engineering Admin/human reviewer must review the new translation again.

## Human approval invariant

A foreign-language Work Instruction can be approved only when:

- Russian translation status is `reviewed`;
- translation fingerprint matches the current source content;
- station assignment exists;
- explicit steps exist;
- Engineering Admin performs the approval action.

AI translation, RAG synthesis and completeness scoring never approve an instruction.

## Operational boundary

MGC continues to be an engineering information/evidence layer. Work Instructions and layouts do not send machine commands to PLCs, robots, conveyors, torque tools or paint equipment.
