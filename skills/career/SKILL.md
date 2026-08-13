---
name: career
description: Career routing handles broad or multi-stage requests across context, direction, market, jobs, materials, applications, communication, interviews, offers, operations, development, governance, and sources. Focused tasks use the owning skill.
---

# Career Router

Route the request to the smallest complete workflow while preserving a shared
career context and pipeline. This skill coordinates other Career skills; it
does not replace their detailed procedures.

## First Response

1. Identify the user's outcome, decision deadline, and current stage.
2. Separate facts already supplied from assumptions and live facts that need a
   current source.
3. Determine whether a private career workspace already exists. Do not create
   one unless persistence is useful and the user authorizes local writes.
4. Choose one primary skill and any necessary follow-on skills from the route
   table below.
5. If the request may lead to an external effect, state where the preview and
   approval boundary will occur.

## Route Table

| User intent | Primary skill | Common follow-on |
| --- | --- | --- |
| Import history, achievements, preferences, or corrections | `career-context` | `career-materials` |
| Explore roles, a pivot, or uncertainty about direction | `career-direction` | `career-market-research` |
| Research an occupation, employer, pay range, or location | `career-market-research` | `opportunity-analysis` |
| Find current openings | `opportunity-search` | `opportunity-analysis` |
| Decide whether to apply to one posting | `opportunity-analysis` | `application-tailoring` |
| Build a baseline resume, profile, portfolio, or case study | `career-materials` | `career-context` |
| Tailor a resume, letter, or short answer | `application-tailoring` | `application-assistance` |
| Inspect or fill an application form | `application-assistance` | `career-pipeline` |
| Plan or reconcile a bounded multi-role application campaign | `application-campaign` | `career-operations` |
| Read and classify career mail or reconcile communications | `career-inbox` | `recruiter-coordination` |
| Find a referral path or draft outreach | `career-networking` | `recruiter-coordination` |
| Handle recruiter messages, slots, or follow-ups | `recruiter-coordination` | `interview-preparation` |
| Prepare, practice, or debrief an interview | `interview-preparation` | `career-pipeline` |
| Compare or negotiate an offer | `offer-negotiation` | `career-pipeline` |
| Track applications or analyze conversion | `career-pipeline` | `career-development` |
| Recover daily state, queue work, or review cross-surface drift | `career-operations` | relevant domain skill |
| Inventory, export, retain, hold, or delete private career data | `career-data-governance` | `career-context` |
| Plan growth, visibility, mentoring, or internal mobility | `career-development` | `career-direction` |
| Add a job, mail, calendar, taxonomy, document, or browser source | `career-source-adapter` | relevant domain skill |

## Non-Negotiable Contract

Read `../../references/operating-contract.md` whenever the request spans more
than one skill, includes persistent data, or may cause an external effect.

- Prefer the user's canonical evidence over generated prose.
- Never invent dates, metrics, employers, titles, credentials, eligibility,
  compensation, references, contact details, or outcomes.
- Label observations, self-reports, derivations, and inferences distinctly.
- Treat a score as a transparent prioritization aid, never as a measured hiring
  probability.
- Keep recruiter chat, proposed time, and confirmed interview distinct.
- Keep drafted, filled, ready, submitted, and accepted distinct.
- Ask only for information that changes the next decision. Batch questions when
  possible.
- Preserve user voice and meaningful qualitative evidence; do not force every
  accomplishment into a number.

## Broad Requests

For requests such as "help me find work" or "manage my career":

1. Establish a short current-state capsule: target, location and remote policy,
   work arrangement, constraints, urgency, available evidence, active leads,
   and desired next outcome.
2. If a private workspace already exists, route first to `career-operations` to
   validate and project durable state. Refresh live sources only after recovery.
3. If the user lacks direction, route next to `career-direction`; if evidence is
   missing, use `career-context`; otherwise use `opportunity-search`.
4. Route communication holds through `career-inbox`, multiple planned
   submissions through `application-campaign`, and privacy lifecycle requests
   through `career-data-governance`.
5. Produce a ranked next-action queue with owners, prerequisites, and stop
   conditions. Do not create a large plan whose first steps cannot be executed.
6. Execute the highest-value authorized local or read-only step in the same turn
   when feasible. Stop at every exact hash-bound external-effect gate.
7. Record only confirmed state changes in the pipeline and reproject before the
   completion report.

## Completion Contract

End with:

- what decision or artifact is now ready;
- evidence used, unknowns, and live-source timestamps;
- the exact pipeline state, if it changed;
- any external effect still awaiting approval;
- the next smallest useful action.

Do not claim that employment, an interview, a response, or any other external
outcome occurred unless directly verified.
