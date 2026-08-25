# Versioned Record Contracts

The frozen Career core validates workspace records and strict JSONL ledgers.
Standalone review contracts name their own deterministic helpers. Templates
illustrate valid records but are not a substitute for validation.

## Shared Encoding Rules

- UTF-8 JSON, one object per nonblank JSONL line.
- No duplicate keys, comments, `NaN`, infinities, binary floats, or integers
  outside the interoperable 53-bit range.
- Decimal money values are strings.
- Timestamps are RFC 3339 with `Z` or a numeric offset.
- Currency is ISO 4217 and timezones are IANA identifiers where applicable.
- Canonical identifiers are lowercase typed UUIDs. Provider identifiers are
  lowercase kebab-case. URLs and provider identifiers are aliases, not entity
  identifiers.
- References resolve inside the workspace. Lists contain no duplicates.
- Append-only revisions point to the immediately preceding revision. A
  correction appends a record; it never edits a prior line.

## `career.evidence_receipt.v1`

Immutable receipt for a bounded source observation.

- `id`: `evidence-<uuid>`.
- `recorded_at`.
- `source`: `kind`, `locator`, `captured_at`, optional `provider_id`,
  `external_id`, and `actor`.
- `integrity`: optional `sha256`, `byte_length`, and `media_type` fields. File
  and provider-record captures require SHA-256.
- optional `selector`, bounded `excerpt` or `summary`, and `redactions`.

File locators are relative to the career workspace. Drive-qualified, UNC,
absolute, or traversal paths fail validation. A user statement needs an
attesting actor role instead of a byte hash. Never place a credential or token
in a locator.

## `career.fact.v1`

Append-only revisions of a stable personal or policy fact.

- `fact_id`, `revision_id`, `supersedes_revision_id`, and `recorded_at`.
- `subject_id`, lowercase dotted `predicate`, and optional `scope`.
- `operation`: `assert` or `retract`; only an assertion carries `value`.
- `confidence`: `low`, `medium`, or `high`, plus `confidence_basis`.
- nonempty `evidence_ids` and `contradicts_fact_ids`.

The current fact is the unique revision tail. A retraction projects no value.
Multiple active, unequal values for the same subject, predicate, and scope must
carry explicit contradiction links. Projection marks them `disputed`; it never
chooses the one with higher confidence.

## `career.opportunity.v1`

Append-only revisions of a stable opportunity entity.

- `opportunity_id`, revision fields, and `recorded_at`.
- source-asserted `title` and `organization`.
- one or more `origins`, each with provider, retrieval time, evidence receipt,
  and an external identifier or URL when available.
- nonempty `evidence_ids`.
- `normalized` employment type, workplace, seniority, distinct work and
  eligible-applicant locations, authorization text, schedule or timezone
  requirements, and optional compensation.
- canonical application URL, published/modified/expiry/last-verified times,
  and the captured source-description hash.
- `normalization_warnings` for unknown, lossy, or disputed mappings.

Raw provider labels and payload stay in linked evidence. The normalized object
never carries pipeline status or outcome. A provider/external-identifier pair
maps to at most one opportunity; a shared canonical URL raises a dedupe warning.

## `career.pipeline_event.v1`

Immutable canonical event. Ledger order, not timestamps, determines current
state.

- `id`, `opportunity_id`, and `previous_event_id` for that opportunity.
- `recorded_at`, `effective_at`, and `actor`.
- interaction-specific `type` and `evidence_ids`.
- `status_before`, `status_after`, and `outcome`.
- optional semantic interaction and schedule state, correction, raw
  provider-status mapping, note, effect result, or ambiguity reconciliation.

Stages are `discovered`, `considering`, `preparing`, `applied`, `screening`,
`interviewing`, `offer`, and `closed`. An outcome appears if and only if the new
stage is `closed`. Rejection is an outcome; an offer is a stage. A recruiter
message or proposed slot cannot be normalized as a confirmed interview.

Normal events cannot regress or follow a closed stage. A correction or reopen
must cite the corrected event and supporting evidence.

## `career.effect_plan.v1`

Append-only approval revisions for one exact external effect.

- `plan_id`, revision fields, creation and revision-recording times, and
  optional opportunity.
- exact `effect`: action, provider, account, target, payload, attachment hashes,
  idempotency key, effect class, data-disclosure manifest, and optional expected
  remote state.
- expiry and approval state.
- `approval_hash` over only the stable approval basis.
- optional human-readable `display_preview`, excluded from the hash.

The basis is canonical UTF-8 JSON:

```json
{
  "schema": "career.effect_approval_basis.v1",
  "plan_id": "...",
  "opportunity_id": "... or null",
  "effect": {},
  "expires_at": "..."
}
```

Serialize with sorted keys, compact separators, ASCII escaping, and non-finite
numbers disabled, then SHA-256 the bytes. A plan revision may change approval
metadata only. Changing target, account, payload, attachment, expiry, or effect
requires a new plan identifier and approval.

Pending means valid but non-executable. Approved requires actor, time, matching
hash, and non-expiry at an explicitly supplied `--as-of` time. Execution is a
separate pipeline event with outcome `succeeded`, `failed`, `ambiguous`,
`denied`, or `cancelled`. An ambiguous result must be reconciled before retry.
Execution binds the latest plan revision recorded at that time, so later
revocation or expiry is enforced without rewriting history.

## `career.provider_descriptor.v1`

Review-time contract for a replaceable provider. It records provider, maintainer,
and source identity; license and service-data findings; authentication and secret
boundary; network destinations and redirects; operations and effect classes;
normalization-relevant freshness and pagination semantics; rate limits, quotas,
costs, attribution, retention and deletion behavior; failure semantics; and a
typed retry contract.

Every operation declares data sent and returned. A single external mutable
effect may use the distinct `plan` and `execute` operations. Multiple effects
use exact `plan:<operation-id>` and `execute:<operation-id>` pairs, where the
operation id is lowercase kebab-case. Every mutable execute requires its exact
same-id plan whose `effect_class` is `local_write`; orphaned or misclassified
pairs are invalid and do not authorize a broader effect. Network destinations
must be absolute HTTP(S) or WebSocket URLs with a parseable host and port, no
whitespace, and no embedded userinfo. Read retries are either disabled or
bounded. Write retries are prohibited or require an idempotency key or
remote-state check, and ambiguous writes stop for reconciliation. A review
descriptor always has `activation: disabled`; enabling a provider is a separate
decision and receipt, not a descriptor edit.

`scripts/provider_descriptor.py` owns this review contract and reuses the
frozen core's strict JSON and diagnostic helpers without adding the descriptor
to the workspace schemas. Validate a descriptor with:

```bash
python3 "$PLUGIN_ROOT/scripts/provider_descriptor.py" validate path/to/provider-descriptor.json --json
```

## Additional Workspace Records

- `career.profile.v1` holds user goals, preferences, constraints, retention,
  and sharing defaults.
- `career.search_policy.v1` holds explicit discovery sources, queries, filters,
  freshness, cadence, and result budget.
- `career.artifact_receipt.v1` versions artifact identity, path, hash, purpose,
  status, source facts, evidence, and derivation.
- `career.application_campaign.v1` freezes a campaign quota separately from its
  primary, reserve, and replacement roster and binds ready items to exact plan
  revisions and submission receipts.
- `career.action.v1` versions due, blocked, done, or cancelled next actions so a
  deterministic queue does not depend on tabs or prose notes.

## Deterministic Projection And Append Proof

`project` derives current fact and pipeline state without rewriting data.
`verify-append` canonicalizes JSON and proves that every old ledger sequence is
an exact prefix of the candidate sequence, allowing newline or key-order
differences while rejecting truncation, edit, reorder, or insertion.

Validation has no wall-clock dependency unless `--as-of` is supplied. Warnings
do not fail by default; `--strict-warnings` promotes them.
