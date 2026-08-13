# Evidence, Facts, Claims, And Artifacts

Career work fails quietly when a polished sentence becomes mistaken for truth.
This contract makes the chain inspectable.

## Record Types

### Evidence receipt

An evidence receipt captures one bounded source observation and how it was
captured. Required fields are:

- `schema`: `career.evidence_receipt.v1`;
- `id`: stable `evidence-<uuid>` identifier;
- `recorded_at`;
- `source`: kind, locator, capture time, and optional provider, external
  identifier, or attesting actor;
- `integrity`: SHA-256 for byte-addressable captures plus optional byte length
  and media type;
- optional selector, bounded excerpt or summary, and redaction notes.

Prefer one decision-relevant observation per receipt. Keep source text out
unless a short excerpt is necessary and licensed or user-owned. Confidence,
assertion, correction, and contradiction belong in `career.fact.v1` revisions.

### Claim manifest

A claim manifest accompanies each generated artifact. Every material claim has:

- stable claim identifier and exact text;
- evidence identifiers;
- disposition: `supported`, `needs_confirmation`, `unsupported`, or `omit`;
- optional derivation note that explains a truthful transformation;
- sensitivity review and artifact location.

The validator accepts `supported` only when every referenced active fact exists,
has usable evidence receipts, and is not retracted or unresolved. An absent
receipt, contradicted fact, or unresolved date conflict fails closed.

### Artifact receipt

Record artifact path, SHA-256, purpose, target opportunity, generated time,
claim-manifest path, evidence snapshot hash, and supersession links. A later
edit creates a new receipt.

## Claim Construction

Use this sequence:

1. Parse the requested artifact into claim slots.
2. Retrieve a small evidence set for each slot.
3. Prefer specific actions, reasoning, scope, and observed results.
4. Preserve qualitative results when no verified number exists.
5. Draft only from selected evidence.
6. Produce a claim manifest before calling the artifact ready.
7. Run `validate-claims` and resolve every failure.
8. Present `needs_confirmation` questions together.

Permitted derivations include changing grammatical person, shortening a source
statement, translating terminology without changing meaning, and calculating a
number from cited inputs with the formula shown. Do not derive a team size,
percentage, revenue, duration, seniority, ownership level, or causal result that
the evidence does not support.

## Conflicts

When sources disagree:

- preserve both receipts;
- identify the exact field and represented date;
- prefer an authoritative source only when its authority is relevant;
- ask the user when the conflict concerns personal history;
- quarantine dependent claims until resolved;
- append the resolution rather than rewriting prior evidence.

Silence is not confirmation. A date missing from a source is `unknown`, not an
open-ended present role.

## Evidence Retrieval

Retrieve by decision, not by volume:

- resume bullet: action, scope, result, and proof;
- interview story: situation, responsibility, actions, reasoning, result,
  reflection, and confidentiality boundary;
- fit analysis: one or more records for each required criterion;
- negotiation: written offer terms, dated market references, preferences, and
  alternatives;
- development plan: repeated gaps, desired role, existing capability evidence,
  and a measurable bridge activity.

Record why an item was selected and what relevant evidence was excluded.

## Confidence Is Not Importance

Fact confidence is `low`, `medium`, or `high` and requires an explicit basis.
The source kind shows whether the receipt is a user statement, file, URL, email,
calendar observation, provider record, or manual capture. A user statement is
valid personal evidence but should not be presented as independently checked.
Retracted or disputed facts remain quarantined.

Importance belongs in the active decision record, not in the confidence field.
A well-supported minor fact can be low importance; a high-impact eligibility
unknown can be urgent but unverified.

## Output Language

Use direct, natural wording that the user can defend in conversation. Avoid
empty superlatives, generic enthusiasm, keyword stuffing, and artificial
metrics. A truthful claim with useful context is preferable to a stronger
sentence that cannot survive follow-up.
