---
name: career-data-governance
description: Career data governance inventories private workspace data and plans disclosure, export, retention, legal hold, scoped deletion, and deletion proof. Excludes automatic evidence cleanup and provider writes without approval.
---

# Career Data Governance

Use this skill for privacy inventory, export, retention review, legal hold,
right-to-delete preparation, workspace cleanup, or deletion verification. Do not
use it for ordinary fact correction, artifact supersession, or automatic removal
of old evidence.

Read `../../references/data-governance.md` and
`../../references/workspace-contract.md`.

## Workflow

1. Bind the exact local workspace, storage owners, provider accounts, requested
   scope, purpose, jurisdiction if supplied, and effective date.
2. Validate and inventory records, artifacts, plans, exports, backups, caches,
   external disclosures, and retention or legal-hold rules without changing
   them.
3. Classify each item as retain, review, export, redact, archive, delete, or
   blocked. Never infer deletion authority from age or supersession.
4. For export, build a bounded package plus a disclosure manifest naming fields,
   recipients, purpose, sensitivity, provenance, hashes, omissions, and limits.
5. For deletion, resolve dependencies and legal holds, explain cryptographic
   erasure limits, and create an exact scoped plan with targets, expected
   effects, backups, provider behavior, proof method, expiry, and hash.
6. Stop for explicit approval of that exact plan. Local and remote deletion are
   separate effects and may need separate approvals.
7. Execute only through a capable approved mechanism. Capture per-target
   receipts, then inventory and query the exact scope again for residuals.
8. Append a deletion or retention receipt without copying deleted sensitive
   content back into the audit record.

## Completion

Report inventory coverage, disclosures, retained and held items, approved scope,
per-target outcomes, residual copies, backup or provider limitations, and what
cannot be proven erased. Never claim secure or cryptographic deletion from a
filesystem unlink, provider acknowledgement, or absence from one query.
