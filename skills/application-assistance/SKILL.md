---
name: application-assistance
description: Application assistance maps reviewed candidate data into a specific form, isolates sensitive or legal questions, previews every external effect, and stops before submission until explicitly authorized.
---

# Application Assistance

Inspect, map, and optionally fill one application while keeping submission as a
separate approved effect.

Read:

- `../../references/application-and-effects.md`
- `../../references/safety-privacy-fairness.md`
- `../../references/record-contracts.md`

## Preconditions

- The user identified the exact opportunity and requested form assistance.
- The opening and canonical application path are verified.
- Authentication uses a user-approved account and host mechanism.
- Current tailored artifacts and claim manifests are available.
- The active tool can distinguish fill from submit. If it cannot, stop.

## Procedure

1. Inspect the form without changing it. Capture sections, required fields,
   limits, prefilled values, attestations, attachments, and final action.
2. Classify every field as supported fact, explicit preference, supported
   derivation, live observation, sensitive or legal, unknown, or optional.
3. Map direct fields to active facts and narrative fields to reviewed artifacts.
4. Batch ambiguous, sensitive, demographic, authorization, compensation, and
   declaration questions for the user. Never infer or choose a nearest option.
5. Draft free text locally and run claim validation.
6. If the user authorized filling, enter reviewed values but do not trigger the
   final action.
7. Re-inspect the complete form, including prefilled or hidden values when the
   interface exposes them.
8. Produce the consolidated review in
   `../../templates/application-review.example.md`.
9. Create a `career.effect_plan.v1` with exact account, target, payload,
   attachments, idempotency key, expiry, and approval hash.
10. Show the immutable preview and stop for explicit approval of that exact
    plan.

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" effect-hash path/to/effect-plan.json --json
```

## If Execution Is Authorized

Re-check target state and plan hash immediately before the final action. Execute
once. Capture provider acknowledgement and record `succeeded`, `failed`, or
`ambiguous`. On ambiguity, verify remote status before any retry.

Update the pipeline to `applied` only after submission acknowledgement. A filled
form remains `preparing`.

## Stop Conditions

Stop when the form requires an unsupported answer, unknown declaration, payment,
new account, terms acceptance, identity verification, unsafe data disclosure,
or an effect that cannot be previewed separately.
