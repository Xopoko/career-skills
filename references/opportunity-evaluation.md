# Opportunity Evaluation

The evaluation answers whether the opportunity deserves the user's next unit of
attention. It does not predict hiring.

## Evidence Matrix

For every explicit or material inferred criterion record:

- criterion text and category;
- required, preferred, or inferred importance;
- weight and why it matters;
- assessment: `met`, `partial`, `gap`, or `unknown`;
- supporting fact and evidence identifiers;
- what would change the assessment;
- whether the criterion belongs in tailoring, interview preparation, or a
  clarification question.

Use `templates/opportunity-analysis.example.json` with `score-fit`. The helper
reports coverage, priority, and fit on known evidence separately. A low coverage
score is a request for information, not a negative verdict.

## Hard Constraints First

Evaluate before weighted criteria:

- verified applicant location and remote policy;
- work authorization or sponsorship language, without legal inference;
- employment and contract arrangement;
- compensation floor and currency when supplied by the user;
- schedule, timezone overlap, travel, on-call, and start timing;
- language or current formal license when truly required;
- safety, scam, ethics, and conflict constraints;
- user-defined dealbreakers.

Hard constraints are `pass`, `fail`, or `unknown`. An unknown high-impact gate
usually yields `clarify`, not `skip` or `apply`.

## Weighted Preferences

Only after hard gates, assess:

- evidence strength for required outcomes;
- level and scope alignment;
- learning value and proof opportunity;
- work content and environment fit;
- compensation and benefit signals;
- employer and role risk;
- application cost, deadline, and reversibility;
- strategic value of the relationship or domain.

Show weights. Do not hide a dealbreaker inside an average or use protected
traits, proxies, prestige, or popularity as fit factors. Here a proxy means a
variable used to infer or stand in for a protected trait. Explicit job-related
location, authorization, schedule, clearance, or language requirements remain
ordinary constraints when assessed exactly as stated.

## Gap Treatment

- `real gap`: capability or requirement absent.
- `proof gap`: capability may exist but evidence is missing.
- `translation gap`: evidence exists in different terminology or context.
- `information gap`: posting or source is ambiguous.
- `preference gap`: the user may not want the recurring work or tradeoff.
- `eligibility gap`: requires exact user input or qualified interpretation.

For each gap choose `clarify`, `mitigate honestly`, `build proof`, `accept`, or
`decline`. Do not disguise a real gap with keyword rewriting.

## Apply / Clarify / Defer / Decline

Recommend:

- `apply` when hard gates pass, evidence is adequate, costs are proportionate,
  and the opportunity serves the user's strategy;
- `clarify` when one cheap answer could change the decision;
- `defer` when evidence repair or timing has higher expected value;
- `decline` when a hard constraint fails, material risk is unacceptable, or the
  work does not serve the user's goals.

Include a candidate angle, top evidence, honest gap treatment, likely interview
themes, and the next action. Record the user's decision, not merely the agent's
recommendation.

## Seniority And Commitment Signaling

For concerns about appearing overqualified, separate objective experience or
scope surplus from an employer's unverified commitment inference and from the
candidate's own risk of underuse. Do not calculate an overqualification
probability, infer age or flight risk, down-title the candidate, erase
chronology, or rewrite historical submissions. Preserve accurate history and
adjust only the salience of current and future surfaces: state deliberate
hands-on scope, why this role is attractive, which responsibilities fit, and
what tradeoffs are intentional.
