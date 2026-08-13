---
name: application-campaign
description: Application campaigns plan and execute bounded multi-role rosters with exact per-role artifacts, approval hashes, outcome accounting, and reconciliation. Excludes blind bulk apply and single-form drafting.
---

# Application Campaign

Use this skill when the user wants a bounded batch, quota, sprint, or campaign
across multiple opportunities. Do not use it for one application, opportunity
discovery, or a request that does not authorize external submissions.

Read `../../references/application-campaigns.md`. For each selected role, also
route artifact work to `application-tailoring` and form work to
`application-assistance`.

## Preconditions

- The private workspace validates and projects without unresolved ledger errors.
- The campaign has a scope, deadline, quota, source policy, and stop conditions.
- Every roster entry identifies one current opportunity and canonical target.
- Quota is a planning target, not permission to lower evidence or safety gates.

## Workflow

1. Freeze a reviewed roster with primary roles, ordered reserves, and explicit
   replacement rules. Keep quota, roster size, and successful submissions as
   separate values.
2. Refresh each candidate role from its canonical source. Remove or hold stale,
   closed, duplicate, ineligible, or ambiguous roles before artifact work.
3. For every active role, create an independent exact plan covering account,
   target, fields, declarations, artifact hashes, disclosures, expiry,
   idempotency key, and expected remote state when available.
4. Validate claims, render final artifacts, and inspect the rendered output.
   A source file hash does not prove the attached or rendered document is right.
5. Present one immutable preview and approval hash per role. Never use one broad
   approval for changed targets, attachments, accounts, or payloads.
6. Execute only approved, hash-matching plans, once each. Capture the provider
   acknowledgement or an exact failure, denial, or ambiguity receipt.
7. Reconcile every attempted role across the provider, inbox, and projected
   pipeline before retrying or reporting completion.
8. Apply the reviewed replacement rule only after the displaced role has a
   recorded disposition. A reserve becomes a new independently approved plan.

## Completion

Report the exact campaign denominator and counts for `succeeded`, `attempted`,
`blocked`, and `skipped`; list each role and receipt; distinguish provider
acknowledgement from local action; show replacements and unused reserves; and
name every unresolved reconciliation gap. Never summarize an attempted click,
filled form, or queued plan as an application submitted.
