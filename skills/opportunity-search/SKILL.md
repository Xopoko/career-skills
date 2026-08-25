---
name: opportunity-search
description: Opportunity search finds, normalizes, filters, deduplicates, and ranks fresh job leads under an explicit or discoverable policy and authorized sources. Excludes fit decisions on one posting and application submission.
---

# Opportunity Search

Find a bounded, reviewable set of live opportunities. Search coverage is always
reported; an empty result never means no openings exist everywhere.

Read:

- `../../references/provider-contract.md`
- `../../references/market-and-opportunity-research.md`
- `../../references/record-contracts.md`

## Inputs

Load or confirm:

- target role families and adjacent titles;
- geography, remote mode, eligible applicant locations, timezone, language,
  authorization, arrangement, schedule, travel, and compensation constraints;
- positive and avoid signals;
- authorized sources, depth, freshness, and result budget;
- active opportunities to deduplicate against.

## Procedure

1. Turn the policy into source-specific queries without weakening hard filters.
2. Select only available, reviewed providers. If none exists, use user-supplied
   postings or bounded web research; do not invent a connector.
3. Record provider, query, retrieval time, pagination, truncation, failures, and
   unsearched sources.
4. Preserve every raw discovery record through an evidence receipt.
5. Normalize the available metadata before filtering, retaining raw values and
   mapping warnings.
6. Use metadata-only discovery only to reduce retrieval cost. Exclude a lead at
   this stage only when an explicit normalized field proves a hard-constraint
   failure; missing detail stays unknown. Fetch the full posting for every
   remaining candidate and preserve either its receipt or the retrieval failure.
   Failed hydration remains unresolved and must not be ranked as complete.
7. Normalize title, organization, employment type, workplace, seniority,
   locations, compensation, dates, source URL, and canonical application URL.
   Keep unknowns and mapping warnings.
8. Apply hard constraints before ranking.
9. Detect exact provider identities, canonical-URL duplicates, and strong
   title-organization candidates. Do not merge ambiguous entities automatically.
10. Rank survivors with visible factors, weights, freshness, and missing data.
11. Refresh finalists from a canonical source and mark removed, expired, or
   unverifiable records.
12. Present a small shortlist and route selected items to
    `opportunity-analysis`.

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" dedupe-opportunities path/to/opportunities.jsonl
python3 "$PLUGIN_ROOT/scripts/career_core.py" validate-workspace path/to/career-data --json
```

## Ranking Boundaries

Ranking is attention allocation, not a hiring probability. Never use protected
traits or proxies. Do not let keyword overlap override eligibility, safety,
location, compensation, or a user-defined dealbreaker.

## Output

Return:

- query, source, and full-detail retrieval coverage;
- hard-filter exclusions with reasons;
- normalized shortlist with freshness and canonical links;
- dedupe and mapping warnings;
- transparent ranking factors;
- unknowns and next refresh date.

Do not submit, save remotely, create accounts, contact anyone, or mutate a
provider during search.
