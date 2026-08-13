# Research Evidence And Safe Operational Claims

This ledger records research that changes the workflow. It does not convert
group-level findings into a personal forecast. Checked 2026-08-13.

## Search Skill And Self-Regulation

Liu, Huang, and Wang (2014) reviewed 47 experimental or quasi-experimental job
search interventions. Participation was associated with 2.67 times higher odds
of employment than control conditions. Interventions combining practical skill
development with motivation enhancement performed better than those missing
one side. Helpful components included search skills, self-presentation,
self-efficacy, proactivity, goal setting, and social support.

- DOI: <https://doi.org/10.1037/a0035923>
- Safe use: pair an executable search action with a goal, feedback loop, and
  optional support mechanism.
- Boundary: component comparisons were heterogeneous and not all components
  were independently randomized. Never use 2.67 as the user's probability or
  promise.

Van Hooft and colleagues (2021) synthesized 378 samples and 165,933 seekers.
Search intensity related to interviews, offers, and employment, but not to job
quality; search quality and self-regulation related to both quantity and quality
outcomes. Much of the evidence is correlational.

- DOI: <https://doi.org/10.1037/apl0000675>
- Safe use: track activity, targeting quality, conversion, and opportunity
  quality separately.
- Boundary: never optimize only for application count or shame a user over a
  quota.

Earlier self-regulation evidence:
<https://doi.org/10.1037/0021-9010.86.5.837>.

## Setbacks And Sustainable Search

Randomized program studies support problem-solving, setback preparation,
positive reinforcement, and social support as components of employment-search
interventions. The contexts are program-level and some are decades old.

- Caplan and colleagues (1989): <https://doi.org/10.1037/0021-9010.74.5.759>
- Vuori and Silvonen (2005): <https://doi.org/10.1348/096317904X23790>
- Cochrane review boundary: <https://doi.org/10.1002/14651858.CD013152.pub2>

Safe use: offer an optional setback plan, sustainable pacing, recovery time,
and support-person check-in. Do not diagnose, promise a mental-health effect, or
substitute search work for clinical care.

## Structured Interview Preparation

Levashina, Hartwell, Morgeson, and Campion (2014) reviewed the structured
employment-interview literature. Useful structure includes job analysis,
consistent job-related questions, question-level evaluation, anchored scales,
and trained or multiple raters. Past-behavior and situational questions measure
partly different content. Evidence for some individual structure components and
probing choices remains incomplete.

- DOI: <https://doi.org/10.1111/peps.12052>
- Safe use: extract competencies, build both past-behavior and situational
  prompts, and assess answers against explicit evidence anchors.
- Boundary: do not score charisma, accent, appearance, or vague "culture fit."

Roulin, Pham, and Bourdage (2023) found in two studies that short asynchronous
video-interview training improved response structure and rated performance,
while unstructured practice alone had little effect.

- DOI: <https://doi.org/10.1016/j.jvb.2023.103912>
- Safe use: teach a concise evidence-bearing response structure before a
  rubric-scored mock and targeted retry.
- Boundary: the finding is mode-specific and did not measure hiring or later job
  performance.

## Negotiation

Cullen, Pakzad-Hurson, and Perez-Truglia (2025) report two field experiments
with more than 3,100 U.S. technology-sector job seekers. A light-touch
encouragement increased negotiation attempts and compensation gains; a large
discount on coaching did not significantly increase attempts.

- NBER Working Paper 33903: <https://www.nber.org/papers/w33903>
- DOI: <https://doi.org/10.3386/w33903>
- Safe use: after a real offer, ask whether the user wants to assess if
  negotiation is appropriate, then inspect negotiability, written terms,
  market evidence, alternatives, priorities, risk, jurisdiction, and channel.
- Boundary: this is a working paper with an unusually highly paid U.S.
  technology sample. Never say everyone should negotiate or promise a gain.

## Occupational Reference Data

O*NET 30.3 is the May 2026 U.S. production database. It includes occupations,
tasks, skills, knowledge, abilities, work context, and metadata.

- Data: <https://www.onetcenter.org/database.html>
- Release archive: <https://www.onetcenter.org/db_releases.html>
- License: <https://www.onetcenter.org/license_db.html>
- Safe use: store release, occupation code, element, scale, and provenance.
- Boundary: treat values as U.S. occupation-level priors, not vacancy
  requirements or proof that a person has a skill. The database is CC BY 4.0;
  separate Career Exploration Tools have different license terms.

ESCO 1.2.1 is the December 2025 multilingual EU classification release. ESCO
concepts have stable URIs, labels in multiple languages, occupation-skill
relations, and mappings to ISCO-08. Its O*NET crosswalk distinguishes exact,
narrow, broad, close, and lower-quality related matches.

- Overview: <https://esco.ec.europa.eu/en/about-esco/what-esco>
- Current release: <https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/esco-v121>
- Crosswalks: <https://esco.ec.europa.eu/en/use-esco/other-crosswalks>
- Safe use: persist URI, version, language, label type, and crosswalk relation.
- Boundary: never silently treat broad or related matches as exact. Verify the
  endpoint dataset because API defaults and documentation can lag a release.

Schema.org `JobPosting` describes source assertions such as title, dates,
employment type, salary, physical location, remote eligibility, qualifications,
and authorization language.

- Vocabulary: <https://schema.org/JobPosting>
- Search implementation guidance:
  <https://developers.google.com/search/docs/appearance/structured-data/job-posting>
- Safe use: preserve source assertions, raw salary, currency and period, remote
  mode, eligible locations, expiry, and plugin derivations separately.
- Boundary: valid markup does not authenticate an employer or opening.

## Scam, Privacy, And Fairness

FTC guidance supports independent verification and a hard stop around paying to
obtain work, fake checks, reimbursement schemes, reshipping, cryptocurrency
tasks, and premature financial or identity disclosure.

- <https://consumer.ftc.gov/articles/job-scams>
- Safe use: show observed warning signals plus independent verification steps.
- Boundary: one heuristic is not proof of fraud.

GDPR Articles 5, 9, 13, 22, and 25 support purpose limitation, minimization,
accuracy, retention limits, special-category protection, transparency, and
privacy by design. Applicability and lawful bases depend on context and
jurisdiction.

- Regulation: <https://eur-lex.europa.eu/eli/reg/2016/679/oj>
- Safe use: local-first storage, explicit purpose and provenance, retention
  review, redaction before transfer, special-category data off by default, and
  no hidden consequential profiling.
- Boundary: these controls do not by themselves establish legal compliance.

EEOC guidance supports excluding protected traits from U.S. hiring decisions
and recognizes application-process accommodation.

- <https://www.eeoc.gov/prohibited-employment-policiespractices>
- <https://www.eeoc.gov/laws/guidance/job-applicants-and-ada>
- Safe use: keep protected traits and proxies out of fit logic. A proxy is a
  variable used to infer or substitute for a protected trait; explicit
  job-related location, authorization, schedule, clearance, and language
  requirements may still be assessed exactly as stated. Offer a
  minimum-disclosure accommodation-request workflow.
- Boundary: U.S.-specific guidance is not a universal legal conclusion.

## Claims This Plugin Must Not Make

- personal probability of hire from a group average;
- application-volume target as the sole success measure;
- diagnosis or treatment claim;
- invented interview story or achievement;
- universal negotiation rule or guaranteed gain;
- candidate fit inferred only from an occupation taxonomy;
- fraud verdict from one warning signal;
- protected-category profiling or autonomous consequential decision;
- unqualified legal conclusion across jurisdictions.
