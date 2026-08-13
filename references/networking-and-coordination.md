# Networking And Recruiter Coordination

Networking should create relevant human context, not mass unsolicited contact.
Recruiter coordination should preserve communication truth and scheduling state.

## Relationship Map

Search only sources the user authorizes. Possible paths include former
collaborators, alumni, community peers, conference contacts, open-source
contributors, hiring team members, recruiters, and second-degree introductions.

For each path record:

- why the person is relevant;
- how the user genuinely knows them or shares context;
- current affiliation and verification date;
- what is being asked;
- privacy and retention boundary;
- confidence and missing facts.

Do not scrape or retain unnecessary contact data, infer private relationships,
or imply familiarity that does not exist.

## Outreach Ladder

Choose the smallest respectful ask:

1. context or role question;
2. brief informational conversation;
3. feedback on fit or proof;
4. introduction to a relevant person;
5. referral only when the relationship and evidence justify it.

A grounded message contains a real connection, specific reason, relevant proof,
low-friction ask, and easy opt-out. Draft one or two variants; do not generate a
spam sequence. Sending remains a communication effect.

## Inbound Recruiter Triage

Extract observed facts:

- sender, address or profile, organization, and claimed role;
- opportunity title, location, arrangement, pay, and stage;
- requested information or action;
- deadline and proposed time;
- links or attachments;
- inconsistencies and verification needs.

Independently verify the sender and opening before sensitive disclosure. Ask a
bounded clarification when role, range, currency, location, authorization, or
process materially affects interest.

## Scheduling Truth

Represent separately:

- `recruiter_contact`: a conversation exists;
- `interview_proposed`: one or more slots were suggested;
- `interview_scheduled`: a slot is confirmed in the authoritative calendar or
  by both parties;
- `interview_completed`: the meeting occurred;
- `follow_up_due`: a local reminder or agreed deadline exists.

Check the actual calendar account in scope. An empty mail search is bounded
coverage, not proof no interaction occurred. Timezone, date, duration, format,
participants, location or meeting link, and preparation needs must be explicit.

## Message Drafting

Keep immediate availability concise. For uncertain pay, ask for the approved
range and currency before stating a number. Keep a private fallback or minimum
out of outbound text unless the user deliberately chooses to disclose it.

Before sending show recipient, account, subject, full body, attachments, data
disclosed, and effect-plan hash. After sending, capture provider acknowledgement
and update the pipeline with an exact communication event.

## Follow-Up

Base follow-up timing on an explicit promise, deadline, or user policy rather
than a universal interval. Reference the prior interaction, add only useful
context, and make one clear ask. Repeated silence is an outcome signal, not
permission for unlimited contact.
