# Career Inbox And Communications Contract

Career inbox work converts bounded communications into evidence and candidate
pipeline observations. It does not treat access to a mailbox as authority to
change it, and it never uses an empty query as proof of complete history.

## Phase 1: Bounded Discovery

Declare the read boundary before opening messages:

- exact account identity and mailbox or folder;
- provider and whether its connector is read-only or mutable;
- query string or structured filters;
- inclusive represented or received date range with timezone;
- pagination, result limits, thread expansion, spam or trash coverage;
- purpose, expected signals, and stop condition.

Search accounts separately. Do not combine results in a way that loses the
receiving account. First retrieve identifiers, thread identifiers, sender,
subject, received time, labels or folder, and a minimal snippet when available.
Record provider truncation, partial pages, and query semantics.

Classify every candidate into exactly one primary class:

| Class | Meaning | Default handling |
| --- | --- | --- |
| `submission_receipt` | A provider or employer acknowledges a submitted application | Hold for opportunity match and submission reconciliation |
| `verification_code` | A time-limited code or link gates an already authorized flow | Hold urgently; never expose or reuse outside the exact flow |
| `status_update` | The application stage or outcome may have changed | Hold for evidence review and pipeline projection |
| `assessment_action` | An assessment, task, questionnaire, or deadline requires action | Hold with deadline and authenticity checks |
| `interview_proposal` | One side proposes one or more interview times | Hold; proposal is not confirmation |
| `recruiter_reply` | A recruiter or hiring contact replied without a clearer class | Hold for thread and opportunity matching |
| `unrelated` | No bounded career relevance is supported | Exclude from further reading and retain no unnecessary content |
| `ambiguous` | Career relevance, sender, target, or required action is uncertain | Hold and inspect cautiously |

Classification is not a remote mutation and does not itself change pipeline
state. Authentication alerts, invoices, marketing, suspicious links, and
identity requests remain ambiguous until safely resolved.

## Phase 2: Held-Item Inspection

Open only actionable or ambiguous candidates. Capture a bounded evidence
receipt with account, message and thread identifiers, sender and reply path,
represented and received times, subject, selector or short summary, and any
provider or opportunity identifiers. Do not persist verification codes, access
tokens, full unrelated threads, or excessive personal content.

Extract action type, deadline with timezone, requested disclosure, attachment
expectation, proposed times, meeting location, and authenticity signals. Do not
click unknown links merely to classify a message. Refresh the canonical
provider or employer surface independently when identity or status matters.

## Communication Matching

Build candidate mappings rather than guessing. Match signals may include:

- provider application identifier or exact external job identifier;
- canonical URL or requisition number;
- account and recipient identity;
- exact thread ancestry and earlier effect receipt;
- organization and title together;
- application timestamp and campaign membership;
- named recruiter affiliation verified from a suitable source.

Rank candidates and show supporting and conflicting signals. An exact provider
identifier can support a confirmed mapping. Same organization, a similar role
title, sender display name, or temporal proximity alone cannot. If multiple
same-company roles exist, keep the communication unmatched until decisive
evidence appears; never update all of them.

## Pipeline Interpretation

Append the narrowest supported observation:

- a submission receipt may reconcile an earlier ambiguous attempt;
- a generic acknowledgement supports `applied`, not `screening`;
- an assessment request may support screening only when the mapping and sender
  authority are established;
- an interview proposal is not a confirmed interview;
- a recruiter reply is not necessarily a stage change;
- silence and absence from a bounded query do not establish `no_response`;
- a rejection needs an exact mapped message or authoritative provider state.

Preserve raw provider wording in evidence and record normalization separately.
Project from append-only events after writing; do not edit earlier events.

## Mutation Gate

Discovery and mutation are separate operations. Each intended reply, send,
archive, label, mark-read, move, delete, or calendar response needs a distinct
effect plan containing exact provider, account, message or thread target,
payload, attachments, disclosures, expected state, idempotency key when
supported, expiry, and approval hash.

One approval does not cover a different thread, account, recipient, body,
attachment, label, or action. If the active connector exposes only read
operations, record `denied` or `unsupported`; do not simulate success through a
different account or UI.

## Post-Write Reconciliation

After an approved write:

1. capture provider acknowledgement, remote identifier, time, and approved hash;
2. rerun an exact query for the target message, thread, sent item, or new state;
3. run a broader but still bounded residual query using sender, recipient,
   organization, provider identifier, or time window;
4. detect duplicates, moved threads, alternate accounts, unmatched replies, and
   contradictory statuses;
5. append only reconciled pipeline evidence and report remaining gaps.

A local click or compose-window closure is not a sent receipt. Failure of the
exact query does not authorize repeating the write. Resolve ambiguity through
provider state and idempotency evidence first.

## Completion Report

State exact coverage per account, query and range; pagination and excluded
folders; classification counts; held items and deadlines; confirmed and
candidate opportunity matches; writes attempted and acknowledged; exact and
broad residual-query results; pipeline changes; and unresolved ambiguity.
