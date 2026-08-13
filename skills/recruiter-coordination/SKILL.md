---
name: recruiter-coordination
description: Recruiter coordination reconciles messages and calendars, distinguishes chat, proposed slot, and confirmed interview, drafts responses, and records follow-ups without sending or booking until approved.
---

# Recruiter Coordination

Maintain precise communication and scheduling state across authorized mail,
calendar, and pipeline sources.

Read:

- `../../references/networking-and-coordination.md`
- `../../references/application-and-effects.md`
- `../../references/safety-privacy-fairness.md`

## Procedure

1. Confirm which account, thread, opportunity, and date range are in scope.
2. Read the relevant thread and actual calendar account. Report bounded coverage.
3. Extract sender identity, claimed affiliation, role, stage, requested action,
   deadline, proposed times, timezone, format, participants, links, and
   attachments.
4. Independently verify the sender or opening before sensitive disclosure.
5. Reconcile pipeline state:
   - a message is `recruiter_contact`;
   - a suggested time is `interview_proposed`;
   - a mutually agreed or authoritative calendar time is
     `interview_scheduled`;
   - attendance is `interview_completed`.
6. Identify contradictions, missing timezone, double booking, account mismatch,
   or unclear stage.
7. Draft the shortest useful response. For uncertain pay, ask for approved range
   and currency before committing; keep private fallbacks out of the draft.
8. Show exact recipient, account, message, scheduling change, and data shared.
9. Create separate effect plans for communication and calendar mutation.
10. Stop for explicit approval at each boundary.

If a recruiter asks for a resume before identifying a role, route asset
selection to `career-materials`. Preserve unknown team and requisition fields,
confirm the artifact owner and recipient, and do not imply role-specific
tailoring. Sending remains a separate exact effect plan.

## After Authorized Execution

Capture service acknowledgement. Re-read the authoritative calendar when a
booking changed. Append exact pipeline events with evidence and schedule only
the follow-up that was agreed or requested.

## Output

Report observed thread state, calendar state, exact stage, conflicts, draft,
effect plans, and next preparation deadline. Do not call a proposed slot a
confirmed interview or an empty search a complete communication history.
