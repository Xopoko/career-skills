---
name: career-materials
description: Career asset creation builds evidence-backed baseline resumes, profiles, portfolios, case studies, accomplishment inventories, and reference briefs. Excludes tailoring to one open role.
---

# Career Materials

Create a reusable baseline asset from active career facts. The output is a
versioned view, not a new source of truth.

Read:

- `../../references/materials-and-applications.md`
- `../../references/evidence-contract.md`
- `../../references/safety-privacy-fairness.md`

## Route By Artifact

- resume: general, chronological, technical, leadership, academic, creative, or
  transition-oriented as justified by the audience;
- profile: headline, summary, experience, skills, projects, and public settings;
- portfolio: index, project case study, proof artifact, or public-safe project
  page;
- evidence asset: accomplishment inventory, story bank, publication list,
  project sheet, or credential index;
- reference asset: permission record, briefing sheet, or contact policy.

Do not create every variant. Choose the asset that unlocks the next decision.

## Procedure

1. Confirm audience, role family, geography, language, format, length, and
   privacy boundary.
2. Retrieve active supported facts and mark disputed or missing items.
3. Select evidence before prose. Ask a compact set of confirmation questions.
4. Choose structure and section order for the audience.
5. Draft in the user's defensible voice. Preserve qualitative results when no
   verified metric exists.
6. Review dates, titles, organizations, credentials, links, confidentiality,
   and internal consistency.
7. Create a claim manifest with exact text and fact identifiers.
8. Validate claims and quarantine anything unsupported.
9. Render and inspect the final file when layout matters.
10. Record artifact hash, purpose, evidence snapshot, and supersession.

## Recruiter Request Without A Role

When a recruiter requests an updated resume but provides no team, role, or
requisition, do not manufacture pseudo-tailoring. Confirm the candidate and
artifact owner, recipient, purpose, role family, and privacy boundary; select a
reviewed baseline asset for that role family; and verify its exact hash. Keep
the opportunity unresolved and preparation separate from sending. Never
retrieve or disclose another person's non-public resume.

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" validate-claims \
  --facts path/to/facts.jsonl \
  --evidence path/to/evidence.jsonl \
  --manifest path/to/claim-manifest.json
```

## Quality Gate

Reject invented metrics, forced superlatives, keyword stuffing, generic mission
praise, unsupported seniority, and unexplained date gaps. Machine-readable
formatting must not destroy human readability. A visual artifact requires a
render check, not source-text inspection alone.

## Output

Provide the artifact, audience, evidence coverage, confirmation gaps, review
findings, claim-validation result, file hash, and next revision trigger.
