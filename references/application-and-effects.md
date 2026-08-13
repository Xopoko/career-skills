# Application Assistance And Effect Boundaries

Application assistance is a high-precision mapping task. It is not autonomous
submission.

## State Machine

Keep these states distinct:

1. `inspected`: form and authentication state observed.
2. `mapped`: fields linked to supported facts or explicit questions.
3. `drafted`: free text exists locally.
4. `filled`: approved values are entered but not sent.
5. `reviewed`: the user saw a consolidated final representation.
6. `ready`: immutable effect plan matches the reviewed target and payload.
7. `submitted`: provider acknowledged the exact action.
8. `verified`: remote application status was refreshed independently.

Do not claim a later state because an earlier UI step succeeded.

## Form Mapping

Classify every field:

- direct supported fact;
- explicit user preference;
- narrative derived from supported facts;
- current opportunity or market observation;
- sensitive, demographic, legal, authorization, pay, or accommodation field;
- unknown or ambiguous;
- optional field to leave blank.

Never infer the last two categories, select a nearest option, or reuse a prior
answer when the wording, jurisdiction, or context changed.

## Consolidated Review

Before external submission show:

- canonical opportunity and target form;
- account and identity being used;
- every populated field, including hidden or prefilled values when inspectable;
- artifact names and hashes;
- sensitive data disclosed;
- unresolved fields and exact omissions;
- required declarations and attestations;
- provider terms or material warnings;
- final action, plan hash, and expiry.

Use `templates/application-review.example.md` and a
`career.effect_plan.v1` record. Approval of a resume draft does not approve the
form. Approval of one plan does not approve a changed form, target, account, or
attachment.

## Execution And Receipt

An adapter may execute only an approved, hash-matching, unexpired plan with an
idempotency key. After execution record provider acknowledgement, timestamp,
plan revision and hash, and result: `succeeded`, `failed`, `ambiguous`,
`denied`, or `cancelled`.

If the result is ambiguous, reconcile remote state before retrying. A browser
timeout is not proof of failure; a local click is not proof of submission.

## Authentication And Accounts

Do not create an account, reset a password, accept terms, solve identity
verification, or change a profile unless that distinct effect is requested and
reviewed. Keep credentials in the host's approved secret mechanism, never in
Career records.

## Accessibility And Accommodation

If the form or interview tool creates an access barrier, route to the
accommodation workflow in `safety-privacy-fairness.md`. Keep the request focused
on the barrier and effective adjustment with minimum disclosure.
