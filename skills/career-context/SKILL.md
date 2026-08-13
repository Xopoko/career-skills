---
name: career-context
description: Career context capture turns source material and user corrections into provenance-linked facts, evidence, preferences, constraints, accomplishments, and reusable story candidates. Excludes drafting a role-specific application.
---

# Career Context

Build or update the user's reusable source of truth. This skill owns evidence
capture and fact revision, not polished application prose.

## Inputs

Ask for only the sources and date range needed for the current outcome. Possible
sources include user statements, existing resumes, portfolios, project notes,
public profiles, work artifacts, email, calendars, or repositories when the user
authorizes them.

Before persistent work, read:

- `../../references/workspace-contract.md`
- `../../references/evidence-contract.md`
- `../../references/record-contracts.md`

## Procedure

1. Define the target context gap and bounded source set.
2. Inspect headings, indexes, metadata, and small excerpts before opening large
   private archives.
3. Create an evidence receipt for each bounded observation. Hash byte-addressable
   captures; use an attesting actor for a user statement.
4. Extract atomic fact candidates: history, responsibilities, achievements,
   skills, projects, education, credentials, eligibility, preferences,
   constraints, goals, compensation facts, or story components.
5. Label confidence and explain its basis. Do not confuse confidence with
   importance.
6. Deduplicate by subject, predicate, scope, dates, and source locator.
7. Surface conflicts, missing end dates, ambiguous ownership, and unsupported
   metrics together for user review.
8. Append fact revisions. Use `supersedes_revision_id` or explicit contradiction
   links; never silently rewrite history.
9. Identify derived artifacts whose claim manifests now depend on superseded or
   disputed facts.
10. Validate the workspace and project current state.

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" validate-workspace path/to/career-data --json
python3 "$PLUGIN_ROOT/scripts/career_core.py" project path/to/career-data
```

## Achievement Interview

When proof is thin, ask in a compact batch:

- What changed, shipped, improved, prevented, or became possible?
- What was personally owned versus shared?
- What constraints and alternatives shaped the work?
- What evidence exists: artifact, message, result, witness, or user confirmation?
- What result is observable, even if not numeric?
- What detail is confidential or unsafe to retain?

Do not invent estimates. Record a qualitative result or an explicit proof gap.

## Corrections

Treat a correction as new evidence. Append the revision, quarantine contradicted
claims, and report dependent artifacts. A generated resume or interview answer
cannot confirm its own content.

## Output

Return:

- records added or revised;
- evidence type and confidence for each material fact;
- conflicts and questions still open;
- affected artifacts;
- validation result and next evidence task.

Do not expose private source content beyond what the user needs to review.
