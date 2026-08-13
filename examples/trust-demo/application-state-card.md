# Synthetic application-state card

This artifact illustrates state precision without representing a real
application, provider, company, or person.

| Field | Synthetic value |
| --- | --- |
| Current state | `attempted; remote submission state unknown` |
| Supporting receipt | `local execution returned ambiguous; provider acknowledgement absent` |
| Unresolved ambiguity | `the provider may or may not have accepted the action` |
| Next authorized action | `inspect provider state; do not retry` |

The branches are deliberately different:

- `approved -> attempted -> provider acknowledgement -> submitted`;
- `approved -> attempted -> ambiguous result -> reconcile before retry`.

`attempted` is not rendered as `submitted`, and reconciliation is required only
for an ambiguous result. Provider evidence is required before the canonical
application state becomes `submitted`.
