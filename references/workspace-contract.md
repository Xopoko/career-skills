# Private Career Workspace Contract

The workspace is optional, local runtime state owned by the user. It is not
plugin source and must not be committed to this repository.

## Default Layout

```text
career-data/
  profile.json
  search-policy.json
  facts.jsonl
  evidence.jsonl
  opportunities.jsonl
  pipeline-events.jsonl
  actions.jsonl
  artifacts/
    index.jsonl
  plans/
    effects/
    campaigns/
  archive/
  README.md
```

Create it with:

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" init-workspace path/to/career-data
```

When `PLUGIN_ROOT` is unavailable, resolve it as two levels above the active
skill directory. The helper refuses to overwrite existing files.

## Data Zones

- `profile.json`: goals, preferences, constraints, and consented retention
  policy. Keep identity fields optional.
- `search-policy.json`: hard filters, positive signals, avoid signals, source
  policy, freshness, and review cadence.
- `facts.jsonl`: append-only fact revisions, retractions, and contradiction links.
- `evidence.jsonl`: immutable source receipts referenced by facts and events.
- `opportunities.jsonl`: source-preserving normalized opportunity records.
- `pipeline-events.jsonl`: hash-chained event history. Reconstruct state; do not
  edit prior lines to make history look cleaner.
- `actions.jsonl`: versioned next actions, dependencies, due times, and
  resolutions used to derive a deterministic work queue.
- `artifacts/index.jsonl`: derived artifact hashes, purposes, source evidence,
  and supersession links. The files themselves may live elsewhere.
- `plans/effects/`: immutable previews for external effects. Expired plans are
  not authorization.
- `plans/campaigns/`: versioned application cohorts with separate target quota,
  primary/reserve/replacement roster, exact effect bindings, and receipts.
- `archive/`: user-directed retention of superseded material.

## Import Rules

1. State the bounded source set and date range before scanning.
2. Read indexes, headings, metadata, and small excerpts before entire private
   archives.
3. Extract candidate records without treating them as confirmed.
4. Deduplicate by source locator, normalized statement, and represented dates.
5. Present conflicts and high-impact unknowns for user review.
6. Write only after the user authorizes persistence.
7. Record source locators that let the user re-check a claim without copying
   more private content than necessary.

Do not import passwords, authentication tokens, private keys, financial account
numbers, identity-document images, medical records, or unrelated conversations.

## Correction And Supersession

Never erase a material correction from history. Append a record whose
`supersedes` or `contradicts` field points to the prior record. Derived artifacts
retain the evidence identifiers and hashes used at generation time, even after
they become stale.

If the user corrects an employment end date, title, metric, or eligibility fact:

1. mark affected evidence as superseded or contradicted;
2. find dependent artifacts through their claim manifests;
3. quarantine unsupported claims;
4. regenerate only the artifacts that still matter;
5. keep the old artifact receipt for auditability unless the user asks to
   delete it.

## Privacy And Retention

Default to local storage and minimum necessary fields. Before sharing data with
a provider, show the fields and purpose. Redact unrelated content. Special or
protected-category data stays absent unless the user deliberately supplies it
for a narrow purpose and chooses a retention rule.

The profile supports:

- `retention.default_days` for short-lived imported material;
- `retention.keep_evidence_until_review` for durable proof;
- `retention.review_on` for an explicit review date;
- `sharing.default` with `local_only` as the safe default.

The plugin must support an intelligible export and user-directed deletion.
Deletion is not implied by removing a derived resume; the underlying evidence
has its own retention decision.

## Concurrency

Treat JSONL append operations as optimistic transactions. The event helper
requires the expected tail hash and writes atomically. If the tail changed,
reload and reconcile rather than overwriting. Other JSON files should be
written through a temporary file and atomic replace when a deterministic helper
owns the write.

## Portability

Use UTF-8 JSON or Markdown, relative artifact paths where possible, ISO 8601
timestamps with offsets, ISO 4217 currency codes, and IANA timezone names. Do
not store machine-specific home paths in reusable templates.
