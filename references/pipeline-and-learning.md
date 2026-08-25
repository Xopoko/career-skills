# Pipeline, Metrics, And Learning

The pipeline is an event-sourced record of what happened, not a retrospective
story edited to fit a conclusion.

## Canonical Stages

`discovered -> considering -> preparing -> applied -> screening -> interviewing -> offer -> closed`

Forward stages may be skipped when reality skips them. A regression or reopen
requires a correction event and evidence. Final outcome is recorded only with
`closed`: `hired`, `rejected`, `withdrawn`, `offer_declined`, `role_closed`,
`expired`, `duplicate`, `no_response`, or `other`.

Interaction event types preserve finer truth, including recruiter contact,
interview proposal, confirmed interview, completed interview, artifact link,
follow-up due, external-effect result, and notes.

## Event Capture

Record only observed changes. Each event includes actor, recorded and effective
times, prior tail, before/after stage, evidence, and optional raw provider status.
Use the atomic append helper with the expected tail identifier. If the tail
changed, reload and reconcile.

Do not overwrite a wrong event. Append a correction citing the original and its
evidence. Use `verify-append` before replacing or syncing ledgers.

## Artifact Lineage

Link each application and interview artifact to:

- opportunity;
- purpose and version;
- artifact hash;
- claim manifest;
- evidence snapshot;
- effect plan and execution receipt when sent;
- superseded artifact, if any.

This enables outcome learning without treating derived prose as a fact.

## Metric Families

Keep separate:

- activity: searches, conversations, applications, practice sessions;
- quality: evidence coverage, targeting quality, opportunity quality, artifact
  review findings;
- conversion: stage-to-stage counts and elapsed time;
- outcome: offer, hire, decline, rejection, withdrawal, expiry, or no response;
- sustainability: planned effort, recovery, and user-reported load;
- learning: repeated criterion, proof, communication, or process gaps.

Counts do not explain causes. Small samples and selection effects make rates
unstable. Never present a conversion change as causal without evidence.

Compute stage reach from the full event history: a later rejection, withdrawal,
or closed tail does not erase an earlier screen, interview, or offer. Every rate
must name its population and denominator. A rejection rate excludes withdrawals,
offer declines, and unresolved applications unless a differently named metric
explicitly defines another population; report those dispositions separately.

## Retrospective

At a bounded cadence:

1. define the period and complete event coverage;
2. reconstruct exact state from events;
3. identify stage bottlenecks and missing outcome data;
4. sample artifacts and opportunities, not only aggregate counts;
5. separate observation from hypothesis;
6. identify the cheapest experiment that distinguishes likely causes;
7. change one or two search, evidence, material, or practice policies;
8. define evaluation and stop conditions;
9. preserve rejected hypotheses.

Examples:

- many low-quality leads -> refine source and hard filters;
- strong fit but few screens -> inspect discoverability, application quality,
  eligibility, timing, and source channel;
- screens but few interviews -> inspect role clarity and evidence selection;
- interviews but no offers -> inspect stage-specific answers, role calibration,
  references, and unresolved constraints;
- repeated proof gaps -> route to `career-development`;
- high activity and worsening opportunity quality -> reduce volume and improve
  targeting.

## Feedback Into Canonical Context

Pipeline outcomes do not automatically modify facts. A new accomplishment,
story, preference, or constraint enters the context only through an evidence
receipt and fact revision. Rejection explanations remain source observations or
hypotheses unless verified.

End each review with a small next-action queue, owners, dependencies, and the
next evidence date.
