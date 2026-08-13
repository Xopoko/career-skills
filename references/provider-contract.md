# Career Provider Contract

Providers are replaceable adapters. They never own the career context, scoring
policy, pipeline truth, or approval decision.

## Required Interface

A provider must implement conceptually separate operations:

1. `describe()` returns capabilities and constraints without authentication.
2. `search(query)` performs a read and returns raw records plus retrieval
   metadata.
3. `get(id)` refreshes one record from its canonical source.
4. `plan(operation)` creates an immutable effect preview without executing it.
5. `execute(plan_id, expected_hash, approval_token)` performs exactly the
   reviewed effect or fails closed.

A read-only provider may omit `plan` and `execute`. A mutable provider must not
combine them.

## Descriptor

Record:

- provider identifier, version, maintainer, source revision, and license;
- service terms and data-use status, including `unknown` when not established;
- authentication mode and secret-storage boundary;
- network destinations and redirect policy;
- supported operations and unsupported filters;
- effect classes for every operation;
- data fields sent and returned;
- rate limits, quotas, credits, and monetary costs;
- attribution obligations;
- caching, retention, and deletion behavior;
- freshness semantics and timestamp units;
- pagination and partial-result semantics;
- failure, retry, and idempotency behavior.

Do not activate a provider merely because its code has an open-source license.
Service terms, fetched-data rights, credentials, runtime safety, and operational
effects require separate review.

## Normalized Job Envelope

Preserve raw and normalized representations. The normalized record includes:

- stable source identity, provider, source URL, canonical application URL, and
  retrieval time;
- title and organization as asserted by the source;
- description and raw source payload or a content hash;
- publication, modification, expiry, and last-verified times with units;
- employment type, seniority, location text, remote mode, and eligible
  applicant locations as separate fields;
- compensation raw text plus normalized minimum, maximum, currency, and period;
- work-authorization language as source text, never a guessed legal conclusion;
- required, preferred, and inferred criteria kept separate;
- normalization warnings and provenance for every derived field;
- pipeline `status` and final `outcome` kept separate.

Unknown is a valid value. Do not rewrite hybrid work as remote, monthly pay as
annual without an explicit formula, or geography as work authorization.

## Search Semantics

1. Apply user-authorized sources and a bounded query.
2. Preserve provider errors, truncation, and pagination limits.
3. Normalize before filtering.
4. Apply hard constraints before weighted ranking.
5. Deduplicate canonical URLs, source identifiers, and strong title-organization
   fingerprints while retaining every source receipt.
6. Refresh finalists from a canonical source.
7. Mark expired, removed, or unverifiable records; do not delete history.
8. Present the source coverage and what was not searched.

## Effect Plan

Every external write plan includes:

- schema, plan identifier, creation and expiry times;
- provider, operation, target, and effect class;
- payload summary and exact sensitive fields disclosed;
- preview suitable for human review;
- expected remote-state hash when available;
- idempotency key;
- `approval_required: true`;
- explicit unsupported or ambiguous fields.

Changing any field invalidates the plan hash and prior approval. Execution must
return a receipt with the plan hash, provider acknowledgement, time, and any
remaining verification gap.

## Retry Rules

Reads may retry with bounded backoff when documented safe. Writes require an
idempotency guarantee or a fresh remote-state check before retry. After an
ambiguous submission result, verify status rather than submitting again.

## Adapter Acceptance Gate

Before activation:

1. pin and review source identity;
2. resolve code and data-license boundaries;
3. inspect scripts, network destinations, secrets, hooks, and dependencies;
4. map every operation to an effect class;
5. test with synthetic data and a disabled executor;
6. prove normalization warnings and failure semantics;
7. prove immutable preview and one-shot approval for writes;
8. document install, disable, update, and removal paths;
9. keep activation a separate explicit step.

Spreadsheet or CSV exports must neutralize untrusted cell values beginning
with `=`, `+`, `-`, or `@` so a spreadsheet cannot interpret provider text as
a formula. Preserve the original value in evidence and document the exported
transformation. Do not duplicate full personal profiles into provider caches
when identifiers or minimized fields are sufficient.

See `source-and-licensing-ledger.md` for reviewed inspirations and deferred
connectors.
