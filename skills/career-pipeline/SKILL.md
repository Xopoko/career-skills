---
name: career-pipeline
description: Career pipeline tracking records event-sourced opportunity status, distinct outcomes, artifact lineage, follow-ups, interviews, offers, conversion metrics, and evidence-backed learning.
---

# Career Pipeline

Record exact state changes and learn from bounded history. Never edit prior
events to make the pipeline look cleaner.

Read:

- `../../references/pipeline-and-learning.md`
- `../../references/record-contracts.md`
- `../../references/workspace-contract.md`

## Update Procedure

1. Identify the opportunity and current event tail.
2. Capture evidence for the observed change: source receipt, user confirmation,
   provider acknowledgement, message, or calendar record.
3. Choose the precise interaction type and canonical stage.
4. Keep final outcome null unless the new stage is `closed`.
5. Distinguish recruiter contact, proposed interview, confirmed interview,
   completed interview, offer, acceptance, rejection, withdrawal, and silence.
6. Link relevant artifact and effect receipts.
7. Create the next event with `previous_event_id` and `status_before` matching
   the verified tail.
8. Append atomically with the expected tail identifier.
9. Project current state and report it.

```bash
python3 "$PLUGIN_ROOT/scripts/career_core.py" append-event \
  --workspace path/to/career-data \
  --event path/to/new-event.json \
  --expected-tail-id event-00000000-0000-4000-8000-000000000000
python3 "$PLUGIN_ROOT/scripts/career_core.py" project path/to/career-data
```

Use `EMPTY` as the expected tail for the first event. If the tail changed, reload
and reconcile. A regression, reopen, or correction requires an explicit
correction event and evidence.

## Review Procedure

1. Define period, opportunity set, and coverage.
2. Validate and reconstruct state from events.
3. Report activity, targeting quality, stage conversion, opportunity quality,
   outcomes, sustainability, and repeated evidence gaps separately.
4. Inspect representative opportunities and artifacts before explaining a
   metric.
5. Separate observations from causal hypotheses.
6. Propose the cheapest experiment that distinguishes likely causes.
7. Change at most a small number of search, material, evidence, or practice
   policies at once.
8. Preserve failed hypotheses and define the next review date.

## Output

For an update, report appended event, evidence, prior and new stage, outcome,
tail identifier, and next follow-up. For a review, report bounded coverage,
counts, conversion with sample sizes, opportunity quality, hypotheses,
experiments, and next evidence date.

Activity is not the objective. Do not optimize solely for application count or
infer why an external party decided without evidence.
