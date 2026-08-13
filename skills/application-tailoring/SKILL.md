---
name: application-tailoring
description: Role-specific tailoring produces truthful resumes, cover letters, short answers, and narrative plans from verified evidence, with claim traceability and artifact review. Excludes browser form mutation.
---

# Application Tailoring

Build only the requested materials for one verified opportunity. This skill
does not fill or submit a remote form.

Read:

- `../../references/materials-and-applications.md`
- `../../references/opportunity-evaluation.md`
- `../../references/evidence-contract.md`

## Required Inputs

- current opportunity record and posting evidence;
- completed hard-constraint and criterion analysis;
- active career facts and relevant baseline asset;
- requested artifact, language, length, format, and deadline;
- known submission channel and any field limits.

If a decisive fact is missing, batch the questions before drafting. Do not
continue from an old role version when the posting changed materially.

## Procedure

1. State the candidate angle and the role outcomes it should prove.
2. Select the smallest evidence set that supports the highest-value criteria.
3. Build a tailoring plan: retain, reorder, translate, expand, shorten, or omit.
4. Draft from selected facts. Terminology may change; meaning and ownership may
   not.
5. Treat each gap honestly: clarify, mitigate, demonstrate adjacent evidence,
   or leave it visible.
6. For a cover letter or short answer, add reasoning the resume cannot show;
   avoid repeating the resume in prose.
7. Run separate truth, role, voice, risk, and format reviews.
8. Create an exact claim manifest and validate it.
9. Render the final output when the destination is PDF, word-processing, or a
   strict visual format.
10. Record artifact hash, purpose, opportunity, source facts, and supersession.

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" validate-claims \
  --facts path/to/facts.jsonl \
  --evidence path/to/evidence.jsonl \
  --manifest path/to/claim-manifest.json --json
```

## Voice Gate

Prefer specific and direct language the user can defend aloud. Remove generic
enthusiasm, copied employer phrasing, empty adjectives, repetitive sentence
patterns, and unsupported causal claims. Do not conceal a material gap with
keyword repetition.

## Output

Return the artifact, tailoring rationale, evidence map, gaps not disguised,
claim-validation result, render result when applicable, and the exact next
effect boundary. Route form mapping to `application-assistance`.
