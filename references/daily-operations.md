# Daily Career Operations Contract

Daily operations is a recovery and decision loop over durable evidence. Its job
is to answer what is true now, what needs attention, and what can be done next
without letting ephemeral interfaces become the source of truth.

## Recovery Before Refresh

Start from the private workspace, not from browser tabs, mail views, a README,
an old report, or remembered chat. Record the workspace locator, validation
time, ledger tails, projection version, active profile and search-policy hashes,
last durable checkpoint, and unresolved integrity warnings.

Run the repository's deterministic validation and projection helpers. When a
candidate workspace extends a previous snapshot, prove append-only continuity.
If validation, tail continuity, or projection fails, stop derived reporting and
repair or quarantine the affected scope. Do not browse broadly in hopes that
live data will repair corrupted local history.

A durable checkpoint includes enough hashes and tail identifiers to detect a
changed fact ledger, opportunity revision, pipeline event stream, artifact
index, policy, or effect plan. Its timestamp alone is insufficient.

## Refresh Plan

After recovery, list decision-relevant freshness gaps. For every read, bind:

- source or provider and exact account;
- opportunity, query, thread, or canonical target;
- represented date or inclusive date range;
- last checked time and freshness requirement;
- expected decision impact;
- pagination, partial-result, and exclusion semantics;
- stop condition.

Refresh the smallest source that can resolve a current decision. Use
`career-inbox` for communications, the opportunity skills for canonical job
state, and provider-specific adapters only within their declared read surface.
Append evidence and events through the owning workflow, then validate and
project again. Keep the pre-refresh checkpoint for comparison.

## Derived Operating View

The operating view is reproducible output, not a writable authority. Derive:

### Current queue

Each action includes identifier, opportunity or campaign, action, reason,
deadline and timezone, priority basis, owner, prerequisites, evidence, approval
boundary, and stop condition. A blocked action stays visible with the blocking
fact; it is not silently replaced by busywork.

### Current state and ever-reached state

Current stage comes from the projected event tail for each opportunity.
`ever_reached(stage)` comes from historical valid events and remains true even
after rejection or closure. Do not count current-stage records and historical
stage reach as the same metric. Corrections and reopened records must follow the
event contract.

### Metrics

For every metric, state population, date window, numerator, denominator,
exclusions, and data-quality gaps. Useful examples include discovered to
considering, applied to screening, screening to interview, acknowledgement
latency, and follow-up completion. A conversion ratio is historical
description, not a predicted hiring probability.

Never create `no_response` merely because time elapsed. It requires an explicit
policy-defined derived label over bounded evidence and must remain distinct from
an observed provider outcome. Empty inbox results or absent notifications are
not evidence of silence outside their declared coverage.

### Campaign and inbox reconciliation

Show campaign quota, roster, reserves, replacements, attempts, acknowledged
successes, blocks, skips, and ambiguous results using the campaign contract.
Show inbox coverage by account and query, held actions, ambiguous items,
confirmed opportunity matches, and candidate matches. Preserve cross-surface
conflicts until resolved.

### Artifact drift

Compare each active artifact receipt and claim manifest with current fact
revisions, opportunity revisions, destination requirements, render hash, and
supersession state. Flag artifacts that are stale, unsupported, mis-targeted,
unrendered, or changed after approval. Drift does not automatically authorize
regeneration or replacement on a remote form.

### Follow-ups

Derive follow-ups from explicit commitments, deadlines, proposed times,
assessment actions, campaign residuals, offer terms, or a user-approved cadence.
Include the communication target and evidence. Do not create repeated messages
from generic timing folklore or infer a response deadline the sender did not
state.

## Prioritization

Apply hard gates before ranking. A practical order is:

1. expiring verification, assessment, interview, offer, or legal deadline;
2. ambiguous external effect that must be reconciled before retry;
3. user-blocking clarification or approval;
4. current high-value opportunity with a freshness or artifact gap;
5. due follow-up grounded in evidence or policy;
6. research, sourcing, or development work with a defined decision use.

Every item needs a cheapest discriminator and a stop condition. A large
application target does not override truth, eligibility, consent, recovery, or
provider safety.

## Ephemeral Surface Rules

Open tabs, spreadsheet rows, task-board cards, dashboards, local reports, and
README notes may point to evidence but are not canonical pipeline events. A UI
badge may be stale. A draft reply is not sent. A filled form is not submitted.
An exported report is a snapshot, not a mutable database. Reconcile each claim
to receipts and projected state before presenting it as current.

## Daily Completion Receipt

Record checkpoint hashes and tails, validation result, projection time, live
sources and coverage, appended record identifiers, current queue, metrics with
denominators, campaign and inbox residuals, artifact drift, pending approvals,
blocked items, and the next review trigger. If no live refresh was needed, say
why and report the freshness basis.
