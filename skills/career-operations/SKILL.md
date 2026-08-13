---
name: career-operations
description: Career operations reconstructs durable workspace state and produces a daily action queue, campaign and inbox reconciliation, metrics, follow-ups, and drift checks. Excludes using dashboards, tabs, or README notes as canonical state.
---

# Career Operations

Use this skill for a daily job-search review, operating dashboard, current-state
recovery, multi-surface follow-up queue, or campaign status. Do not use it for a
single opportunity decision or as a substitute for the underlying domain skill.

Read `../../references/daily-operations.md` and
`../../references/operating-contract.md`.

## Workflow

1. Validate the private workspace, prove append-only integrity when a prior
   checkpoint exists, and project current state before any live refresh.
2. Recover the last durable checkpoint, active policy, unresolved ambiguity,
   pending effect plans, and source coverage. Treat dashboards, open tabs,
   README text, and stale exports only as leads.
3. Refresh live sources only when the projected state shows a decision-relevant
   freshness gap. Bound each account, provider, query, opportunity, and date.
4. Reconcile new evidence through the owning skill, then revalidate and
   reproject. Do not write a derived status directly.
5. Derive the action queue, current stage, ever-reached stage metrics, campaign
   counts, inbox holds, artifact drift, deadlines, and follow-ups from the
   recovered records and receipts.
6. Rank actions by hard deadline, blocked external effect, decision value,
   freshness risk, and effort. Attach owner, prerequisite, evidence, and stop
   condition to every action.
7. Execute only authorized local work. Route external effects to their exact
   hash-bound preview and approval gates.

## Completion

Return the checkpoint and projection used, live coverage and timestamps, exact
queue, current versus historical metrics, campaign and inbox residuals,
artifact drift, pending approvals, and next review time. Never infer
`no_response` from elapsed time or missing results, and never report a tab,
dashboard, or draft note as canonical state.
