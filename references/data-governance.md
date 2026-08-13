# Career Data Governance Contract

Career runtime data is private user-owned state. Governance makes its location,
use, disclosure, retention, export, and deletion intelligible without turning a
cleanup request into silent evidence destruction.

## Scope And Ownership

The public plugin repository contains code, contracts, synthetic fixtures, and
templates only. Personal facts, evidence, opportunities, communications,
artifacts, effect plans, credentials, and provider receipts belong in the local
private workspace or an explicitly authorized service.

Before governance work, identify the workspace root, device or storage owner,
provider accounts, synchronized folders, export destinations, backup surfaces,
and user-requested scope. Do not scan unrelated home folders, mailboxes, cloud
drives, or accounts merely because they may contain career data.

## Read-Only Inventory

Create a bounded inventory before proposing changes. For each item or collection
record:

- stable locator or identifier and owning system;
- data class, represented person, purpose, and sensitivity;
- source and provenance;
- byte size or record count when available;
- creation, represented, last-used, and retention-review times;
- active dependencies and supersession state;
- disclosed recipients and provider retention behavior;
- backup, synchronization, cache, and derived-copy relationships;
- legal hold or preservation requirement, including `unknown`;
- integrity hash when byte-addressable and safe to compute.

Inventory metadata should not duplicate the sensitive content it describes.
Credentials, verification codes, private keys, and identity documents require
special handling and should not be copied into Career records.

## Disclosure Manifest And Export

An export plan names purpose, requester, recipient, transport, expiry, and exact
included records or fields. Its disclosure manifest includes:

- source workspace checkpoint and export time;
- file or record identifiers, media types, sizes, and hashes;
- fields disclosed, redactions, and sensitivity classes;
- provenance and represented date ranges;
- derived artifacts and their claim manifests;
- omitted collections and reasons;
- recipient, intended use, onward-sharing limits, and retention expectation;
- encryption or access-control method when used;
- known completeness and portability limitations.

Minimize to the purpose. A complete workspace export is not automatically the
right attachment for an employer, recruiter, backup provider, or support case.
Validate the package and inspect readable outputs before release. Sending or
uploading the export remains a separate hash-bound external effect.

## Retention Review

Retention rules are review triggers, not automatic deletion authority. For each
class, consider continuing purpose, user preference, evidence value, dispute or
audit need, active applications, contractual or legal obligations, provider
behavior, and dependency on derived artifacts.

Possible decisions are retain until a dated review, archive, minimize or redact,
export then delete, delete after dependency resolution, or hold. Preserve the
decision basis, actor, effective date, and next review. Superseded evidence and
closed opportunities may still be needed to explain claims, corrections,
campaign counts, or external effects.

## Legal And Preservation Holds

A legal hold means deletion is blocked for the exact covered scope until an
authorized release is recorded. The plugin does not invent legal duties or give
jurisdiction-specific legal advice. If a plausible dispute, regulatory request,
contractual preservation clause, litigation hold, or user instruction exists,
mark the scope `hold` or `unknown` and seek appropriate guidance before
deletion.

Do not use a broad possible hold to retain unrelated data indefinitely. Record
the authority, scope, start date, review date, custodian, and release condition
when known.

## Exact Scoped Delete Plan

Deletion is a destructive external effect. The immutable plan includes:

- plan and revision identifiers, creator, expiry, and approval hash;
- exact local paths or remote identifiers, resolved without traversal or broad
  globs;
- account, provider, device, and data owner;
- data classes and represented date range;
- dependencies, derived copies, synchronized replicas, caches, and backups;
- legal-hold result and unresolved authority;
- action per target: redact, unlink, trash, purge, revoke, or provider request;
- expected recoverability and rollback path;
- provider acknowledgement semantics and estimated propagation delay;
- post-delete proof queries and accepted residuals;
- audit receipt fields that avoid recreating deleted content.

Display exact targets and expected consequences. Any target, account, action,
backup rule, or proof-method change invalidates approval. Do not combine local
file deletion and remote provider deletion under a vague single action.

## Cryptographic Erasure Limits

Deletion proof must match the mechanism:

- unlinking a file removes a directory entry, not necessarily every storage
  block, journal, snapshot, backup, thumbnail, or synchronized copy;
- overwriting is unreliable on SSDs, copy-on-write filesystems, managed cloud
  storage, and remapped blocks;
- encryption at rest does not prove erasure unless the relevant keys are
  uniquely scoped, destroyed, and unrecoverable from backups or escrow;
- provider deletion acknowledgements prove only the provider's stated action,
  subject to its retention, replication, legal, and backup policies;
- a zero-result search proves absence only within that exact account, query,
  range, index, and time.

Use terms such as `logical deletion`, `moved to trash`, `provider-acknowledged
deletion`, or `key destruction` precisely. Never promise forensic or
cryptographic erasure without evidence covering keys, replicas, backups, and
the underlying storage model.

## Execution And Post-Delete Proof

Immediately before execution, resolve all targets again, confirm they remain in
scope, verify the approved hash and expiry, and stop if dependencies or holds
changed. Execute per target and collect result, time, mechanism, actor,
recoverability, provider identifier, and errors.

Then:

1. inventory the exact local or remote target again;
2. run the plan's exact query and a bounded residual query;
3. check declared synchronized copies, trash, caches, exports, and backups when
   authorized and observable;
4. validate remaining workspace ledgers and projection;
5. record residuals, propagation windows, inaccessible surfaces, and next check;
6. preserve a receipt containing identifiers, hashes of the approved plan, and
   outcomes, not the deleted secret or content.

Partial deletion is not complete deletion. A provider timeout is ambiguous, not
failure or success. Do not repeat destructive calls until remote state and
idempotency behavior are reconciled.

## Non-Deletion Events

Correcting a fact appends a revision. Superseding an artifact updates its index.
Closing an opportunity appends a pipeline event. Archiving changes access or
organization. None of these operations implies deletion of the underlying
evidence. Never auto-delete evidence based on age, status, campaign completion,
or a failed application.

## Completion Receipt

Report scope and exclusions, inventory checkpoint, retention decisions, holds,
export disclosure manifest, approved delete-plan hash, per-target results,
logical and provider acknowledgements, residual queries, recoverability,
backup and replica limitations, and any claim that remains unprovable.
