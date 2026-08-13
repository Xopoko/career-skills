---
name: career-inbox
description: Career inbox reconciliation reads bounded accounts and queries, classifies job-search communications, maps candidates to opportunities, and gates exact message mutations. Excludes general mail cleanup and recruiter prose drafting.
---

# Career Inbox

Use this skill for application receipts, recruiter mail, assessments,
verification messages, interview proposals, and career inbox reconciliation.
Do not use it for unrelated personal mail, broad mailbox cleanup, or composing a
reply without first resolving its exact conversation and opportunity.

Read `../../references/inbox-and-communications.md`. Route reply wording or
scheduling to `recruiter-coordination` after reconciliation.

## Workflow

1. State phase 1 before reading: exact account, bounded query, date range,
   provider, expected coverage, and stop condition.
2. Read only matching metadata and small excerpts, then classify each item as
   `submission_receipt`, `verification_code`, `status_update`,
   `assessment_action`, `interview_proposal`, `recruiter_reply`, `unrelated`,
   or `ambiguous`.
3. Hold actionable and ambiguous items. Do not mutate, reply, archive, or infer a
   pipeline transition during discovery.
4. In phase 2, inspect only held items deeply enough to identify account,
   thread, sender, represented time, provider identifiers, role cues, required
   action, deadline, and safety concerns.
5. Produce ranked communication-match candidates. Confirm the exact opportunity
   from identifiers and evidence; same company or similar title is insufficient.
6. Append only supported pipeline observations. Keep recruiter chat, proposed
   time, confirmed interview, and authoritative calendar state distinct.
7. For any send, reply, label, archive, delete, or other mutation, create a
   separate exact-target plan and hash. If the provider is read-only, report
   denial and stop.
8. After an approved write, capture the provider receipt, rerun the exact query,
   then a bounded broader residual query to detect moved, duplicated, or
   unmatched items.

## Completion

Report the accounts and ranges covered, counts by taxonomy, held actionable and
ambiguous items, confirmed mappings, candidate mappings, pipeline events, and
residual queries. Name provider limitations. Never state that the inbox is
clear, a reply was sent, or a role changed stage without exact evidence.
