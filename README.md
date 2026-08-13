# Career Skills

Career Skills is a portable, evidence-first operating layer for career decisions and
job search. It keeps reusable facts separate from generated artifacts, live
market observations separate from durable evidence, and local drafts separate
from external effects.

It ships as 20 focused Agent Skills behind one router, plus a network-free
validator for career facts, evidence, opportunities, artifacts, campaigns,
due actions, pipeline events, and approval-gated effects.

The plugin supports people who are exploring direction, actively searching,
changing role families, preparing for interviews, comparing offers, or building
longer-term career capital. It is not a legal, tax, immigration, medical, or
mental-health decision maker.

## Install

Claude Code:

```text
/plugin marketplace add Xopoko/career-skills
/plugin install career@career-skills
```

Codex, Cursor, and other Agent Skills hosts can install from this repository or
through a reviewed pin in Plug'n Skills. See `docs/INSTALL.md`.

## Skill Map

- `career`: route broad and multi-stage requests.
- `career-context`: capture facts, proof, preferences, constraints, and stories.
- `career-direction`: compare role families, pivots, and small experiments.
- `career-market-research`: research occupations, employers, pay, and geography.
- `opportunity-search`: find, normalize, filter, deduplicate, and rank leads.
- `opportunity-analysis`: map a posting to evidence, constraints, risks, and gaps.
- `career-materials`: build baseline resumes, profiles, portfolios, and briefs.
- `application-tailoring`: tailor truthful artifacts for one opportunity.
- `application-assistance`: review and fill forms behind an external-action gate.
- `application-campaign`: run bounded multi-role rosters with per-role approval and receipts.
- `career-inbox`: classify and reconcile bounded job-search communications.
- `career-networking`: find warm paths and draft grounded outreach.
- `recruiter-coordination`: reconcile messages, scheduling, and follow-ups.
- `interview-preparation`: prepare evidence-backed stories and practice loops.
- `offer-negotiation`: normalize and compare terms, then plan a counter.
- `career-pipeline`: maintain event-sourced state and learn from outcomes.
- `career-operations`: recover durable state and derive the daily queue and drift view.
- `career-data-governance`: inventory, export, retain, hold, and delete private career data.
- `career-development`: turn repeated gaps into bounded growth experiments.
- `career-source-adapter`: specify and vet new sources without auto-activation.

## Core Invariants

- A generated artifact is never a new fact by itself.
- Every material claim is supported, explicitly self-reported, marked for
  confirmation, or omitted.
- Search ranking exposes hard filters, factors, weights, missing data, and
  freshness; it is not a probability of success.
- Opportunity `status` and final `outcome` are separate fields.
- Drafting, filling, sending, scheduling, submitting, accepting, paying, and
  deleting are distinct effects.
- External effects require an immutable preview and explicit authority at that
  exact boundary.
- Sensitive and equal-opportunity fields are never inferred.
- Current postings, people, pay, law, platform behavior, and employer facts are
  refreshed and date-stamped when they affect a decision.

## Local Workspace

The deterministic helper creates a private workspace without overwriting an
existing file:

```bash
python3 scripts/career_core.py init-workspace path/to/career-data
python3 scripts/career_core.py validate-workspace path/to/career-data
```

The workspace is user-owned runtime data. Do not commit it to this repository.
See `references/workspace-contract.md` before importing personal information.

## Deterministic Helpers

```bash
python3 scripts/career_core.py validate-record record.json
python3 scripts/career_core.py dedupe-opportunities opportunities.jsonl
python3 scripts/career_core.py score-fit analysis.json
python3 scripts/career_core.py validate-claims --facts facts.jsonl --evidence evidence.jsonl --manifest claims.json
python3 scripts/career_core.py append-event --workspace path/to/career-data --event event.json --expected-tail-id EMPTY
python3 scripts/career_core.py project path/to/career-data
python3 scripts/career_core.py ops-brief path/to/career-data --as-of 2026-08-13T12:00:00Z
python3 scripts/career_core.py verify-append --base old-data --candidate new-data
python3 scripts/career_core.py effect-hash effect-plan.json
python3 scripts/career_core.py check-triggers
python3 scripts/token_report.py
```

These helpers do not browse, authenticate, send, book, submit, accept, pay, or
delete. Provider adapters remain separate and must satisfy the contract in
`references/provider-contract.md`.

## Validation

```bash
python3 scripts/validate_package.py
python3 -m unittest discover -s tests
python3 scripts/career_core.py check-triggers
```

The first release is source-only and ships no live job-board, mail, calendar,
browser, payment, or submission connector.
