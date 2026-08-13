# Synthetic claim manifest card

This compact artifact shows the exact boundary exercised by the public trust
demo. Every statement is fictional.

| Claim | Fact | Evidence source | Fact scope | Sensitivity | Result |
| --- | --- | --- | --- | --- | --- |
| `Reduced review turnaround from four days to two days for a fictional product release.` | no fact linked | not reachable | not linked | synthetic fixture | `FAIL - unsupported` |
| `Reduced review turnaround from four days to two days for a fictional product release.` | `fact-a3333333-3333-4333-8333-333333333333` | `evidence-a2222222-2222-4222-8222-222222222222`; `user_statement`; `fixture:fictional-review-turnaround` | `{"context":"synthetic_demo","period":"2026"}` | synthetic fixture | `PASS - evidence linked` |

Run `python scripts/run_trust_demo.py` to reproduce both results. The exact
machine-readable records are [facts.jsonl](facts.jsonl),
[evidence.jsonl](evidence.jsonl),
[unsupported-claim-manifest.json](unsupported-claim-manifest.json), and
[supported-claim-manifest.json](supported-claim-manifest.json). None contains a
real resume, employer, recruiter, or application.
