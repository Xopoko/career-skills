---
name: career-source-adapter
description: Career source adapters specify and vet new job, mail, calendar, taxonomy, document, or browser providers through capability, normalization, privacy, licensing, and effect contracts. Excludes automatic activation.
---

# Career Source Adapter

Design or review a provider without allowing it to own career truth or bypass
effect gates. This skill does not install, authenticate, or activate a source by
default.

Read:

- `../../references/provider-contract.md`
- `../../references/source-and-licensing-ledger.md`
- `../../references/record-contracts.md`
- `../../references/safety-privacy-fairness.md`

## Intake

State:

- user outcome and required operations;
- source identity and immutable revision when code is involved;
- service endpoints, authentication, terms, data rights, and jurisdiction;
- runtime host and install boundary;
- data fields needed and minimum disclosure;
- whether each operation is read, local write, remote write, communication,
  submission, payment, or delete.

## Review Procedure

1. Call or inspect `describe` before authentication or execution.
2. Pin source and review license at file and data boundaries. An open-source code
   license does not authorize fetched data or service use.
3. Inspect dependencies, scripts, installers, hooks, network destinations,
   redirects, secret access, telemetry, caching, and update behavior without
   executing candidate instructions.
4. Enumerate operations and unsupported filters.
5. Define raw-to-normalized mapping for every field. Preserve raw evidence and
   emit warnings for unknown or lossy mappings.
6. Specify pagination, freshness, timestamp units, rate limits, quota, cost,
   partial results, retry, and idempotency behavior.
7. Prove canonical source identity, origin collision handling, and dedupe rules.
8. For writes, separate `plan` and `execute`; bind exact target, account,
   payload, attachments, expiry, and idempotency key into the approval hash.
9. Test synthetic fixtures with execution disabled, including failures and
   ambiguous results.
10. Document install, enable, credential, disable, update, and removal paths.
11. Validate the adapter, then request a separate activation decision.

## Rejection Conditions

Reject or isolate a candidate that auto-submits, skips permissions, combines
preview with execution, persists credentials in career data, selects sensitive
answers, retries ambiguous writes, hides paid operations, has unresolved code
reuse rights, or cannot report source coverage and failure semantics.

## Output

Produce a descriptor, operation/effect matrix, data-flow and disclosure map,
normalization contract, license and terms findings, threat review, synthetic
test results, install lifecycle, residual risks, and `adopt`, `adapt`, `defer`,
or `reject` verdict. Activation is never automatic.
