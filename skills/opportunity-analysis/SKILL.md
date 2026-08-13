---
name: opportunity-analysis
description: Opportunity analysis maps a posting to verified evidence, hard constraints, gaps, employer signals, scam risks, and a transparent apply, clarify, defer, or decline recommendation. Triggers on pasted text or a job URL.
---

# Opportunity Analysis

Decide whether one opportunity deserves the next unit of attention. Do not turn
text similarity into a prediction.

Read:

- `../../references/opportunity-evaluation.md`
- `../../references/market-and-opportunity-research.md`
- `../../references/safety-privacy-fairness.md`

## Procedure

1. Capture the posting text or fetch the canonical URL when permitted. Record
   source, retrieval time, publication or expiry, and any discrepancies.
2. Verify the opening and organization before requesting sensitive data.
3. Parse required, preferred, and inferred criteria separately. Extract role
   outcomes, level, scope, location, remote mode, eligible locations,
   arrangement, schedule, pay, application path, and stated process.
4. Apply hard constraints first: eligibility, location, arrangement, pay floor,
   timing, schedule, safety, and user dealbreakers.
5. Retrieve active facts for each important criterion. Classify `met`, `partial`,
   `gap`, or `unknown`; cite fact and evidence identifiers.
6. Classify gaps as real, proof, translation, information, preference, or
   eligibility gaps.
7. Research only employer or role facts that could change the decision. Label
   source claims and inferences.
8. Record scam and exploitation signals as observations plus verification
   steps, not a verdict from one heuristic.
9. Score only after documenting weights and hard gates.
10. Recommend `apply`, `clarify`, `defer`, or `decline`, then state the cheapest
    fact that could change it.

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" score-fit path/to/opportunity-analysis.json
```

## Output

Include:

- canonical opportunity and freshness;
- role and hiring-problem summary, with inferred parts marked;
- hard-constraint results;
- evidence matrix with coverage;
- strengths, gaps, risks, and unknowns;
- transparent score inputs, if scoring helps;
- recommendation and confidence limits;
- honest candidate angle and likely interview themes;
- next action and expected pipeline event.

Route current market questions to `career-market-research`, artifact creation to
`application-tailoring`, and form work to `application-assistance`.
