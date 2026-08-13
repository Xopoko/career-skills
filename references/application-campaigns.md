# Application Campaign Contract

An application campaign is a bounded collection of independently reviewable
applications. It is not a license for unattended bulk submission. The system
optimizes for truthful, suitable, verifiable applications, not raw volume.

## Campaign Record

Record the campaign identifier, created time, owner, purpose, deadline, target
quota, maximum attempts, source and eligibility policy, allowed accounts,
review cadence, stop conditions, and status. Bind the campaign to the projected
workspace tail used to build it.

Keep these measures distinct:

- `quota`: desired number of acknowledged submissions;
- `roster`: reviewed primary opportunities intended to satisfy the quota;
- `reserves`: ordered candidates that may replace displaced roster entries;
- `replacements`: reserves actually promoted under a recorded rule;
- `attempted`: plans for which an executor made the approved external call;
- `succeeded`: attempts with provider acknowledgement;
- `blocked`: candidates that could not pass a required gate;
- `skipped`: reviewed candidates deliberately not attempted.

A quota of ten does not mean ten roles may be found, tailored, or submitted
without individual review. A roster can exceed the quota only when the reason
and replacement policy are explicit. Denominators must name the population:
`6 succeeded / 8 attempted / 10 primary roster`, for example.

## Roster And Replacement Rules

Each roster or reserve entry includes the opportunity identifier and revision,
canonical URL, organization and title as source assertions, freshness receipt,
eligibility result, fit decision, priority, dependencies, and disposition.

Define replacement triggers before execution, such as canonical closure,
duplicate detection, hard-constraint failure, unsupported required answer,
artifact failure, provider denial, or user removal. Do not replace a role merely
because its form takes longer than expected or because a reserve is easier.

Promotion from reserve to roster is a state transition, not a submission. It
requires a fresh canonical check and its own artifacts, plan, hash, preview,
and approval. Preserve why the original role left the roster.

## Per-Role Gate

Every role must pass all of these gates independently:

1. The opportunity is current, canonical, in scope, and not already represented
   by an equivalent active application.
2. Hard constraints and sensitive or legal unknowns are resolved or explicitly
   held; scoring cannot override them.
3. Tailored content is derived from active facts and has a valid claim manifest.
4. The final attachment bytes are hashed after rendering. Inspect pagination,
   clipping, fonts, links, language, filename, and role-specific content.
5. The complete form review includes account, target, every field, declarations,
   attachments, disclosures, omissions, and final action.
6. A distinct unexpired `career.effect_plan.v1` matches the exact reviewed
   payload. Approval is bound to its hash and cannot cover later edits.

If any gate fails, classify the role as blocked or skipped with a reason. Never
reuse another role's form answers, artifact hash, approval, or acknowledgement.

## Execution Ledger

Before an external call, verify the current target state, account, plan hash,
approval actor and time, expiry, attachment bytes, and idempotency key. Execute
once. Record:

- attempt identifier, role, plan revision, and approved hash;
- executor and account;
- start and completion times;
- provider request or idempotency identifier when available;
- provider acknowledgement, status text, and resulting locator;
- result: `succeeded`, `failed`, `ambiguous`, `denied`, or `cancelled`;
- screenshots or evidence receipts needed to verify the outcome;
- verification gaps and whether retry is prohibited.

Only `succeeded` contributes to the successful-submission quota. Failed,
denied, cancelled, and ambiguous calls still count as attempted when a remote
call occurred. A blocked or skipped role was not attempted. Do not report an
aggregate success count without the role-level receipts behind it.

## Cross-Surface Reconciliation

After every attempt, and again before closing the campaign, reconcile:

1. the provider's application or confirmation surface;
2. the exact account inbox for a submission receipt or verification request;
3. the local effect receipt and evidence identifiers;
4. the projected pipeline stage and previous event tail;
5. the campaign roster disposition and counters.

Conflicts remain visible. A provider acknowledgement can establish submission
even before email arrives. An email receipt may resolve an ambiguous browser
result when the opportunity, account, time, and provider identifiers match. A
local click, success toast without stable identity, or sent attachment alone is
not sufficient.

Do not retry an ambiguous call until the remote status and inbox have been
checked. If uncertainty remains, keep `ambiguous`, stop that role, and protect
the idempotency key from reuse.

## Stop Conditions

Pause the campaign when approval scope changes, the projected workspace tail
changes incompatibly, account identity is uncertain, provider behavior changes,
cost or terms appear, required truth is missing, render QA fails, duplicate
submissions become possible, or success cannot be reconciled. Reaching the
quota stops further submissions unless the user approves a new campaign plan.

## Campaign Closeout

Close with a role-level table containing primary or reserve origin, final
disposition, attempt result, provider acknowledgement, pipeline event, and next
action. State quota attainment separately from roster processing. Preserve
unused reserves, unresolved ambiguous attempts, and evidence needed for later
follow-up; never rewrite them as successes or delete them for a cleaner report.
