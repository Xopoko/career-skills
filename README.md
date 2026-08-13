<p align="center">
  <img src="assets/icon.png" width="128" alt="Career Skills logo">
</p>

<h1 align="center">Career Skills</h1>

<p align="center">
  Evidence-first career and job-search workflows for decisions you can explain
  and actions you control.
</p>

<p align="center">
  <strong>Codex</strong> &middot; <strong>Claude Code</strong> &middot;
  <strong>Cursor</strong> &middot; <strong>Agent Skills</strong>
</p>

<p align="center">
  <a href="https://github.com/Xopoko/career-skills/actions/workflows/ci.yml"><img src="https://github.com/Xopoko/career-skills/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-F59E0B.svg" alt="MIT license"></a>
</p>

Career Skills is a portable skill system for career direction, job discovery,
applications, interviews, offers, and long-term career development. It gives a
general-purpose agent a durable operating model: facts stay linked to evidence,
uncertainty remains visible, and drafts do not silently become external actions.

The repository contains 20 focused Agent Skills behind one router, shared
references and templates, and a deterministic, network-free Python toolkit.
It does not ship a job-board scraper, mail client, calendar integration, or
automatic application bot.

## Quick Start

### Ask Your Agent

Paste this into an agent that can install local plugins:

> Install Career Skills from https://github.com/Xopoko/career-skills on this
> computer. Validate the source first, preserve the complete repository so the
> skills can reach their bundled references, templates, and scripts, configure
> it only for the current host, and report exactly what changed. Do not enable
> mail, calendar, browser, or job-source access.

### Codex

```bash
codex plugin marketplace add Xopoko/career-skills
codex plugin add career@career-skills
codex plugin list
```

### Claude Code

Run these slash commands inside Claude Code:

```text
/plugin marketplace add Xopoko/career-skills
/plugin install career@career-skills
/reload-plugins
```

The command-line equivalent is:

```bash
claude plugin marketplace add Xopoko/career-skills
claude plugin install career@career-skills
claude plugin list
```

### Cursor

Install the complete repository as a local plugin. Create the parent directory
first if it does not exist:

```bash
git clone https://github.com/Xopoko/career-skills.git "$HOME/.cursor/plugins/local/career"
cd "$HOME/.cursor/plugins/local/career"
python scripts/validate_package.py
```

Restart Cursor or run **Developer: Reload Window**, then verify **Career
Skills** under **Customize**. Do not copy only the directories under `skills/`;
the workflows also use the repository-level `references/`, `templates/`, and
`scripts/` directories.

See the [complete installation guide](docs/INSTALL.md) for local-checkout and
host-specific details.

## Skill Map

| Stage | Skills | What the agent can help produce |
| --- | --- | --- |
| Route and govern | `career`, `career-context`, `career-operations`, `career-data-governance` | A bounded plan, reusable fact and evidence records, a daily queue, and explicit data-handling rules |
| Explore and learn | `career-direction`, `career-market-research`, `career-development`, `career-source-adapter` | Target hypotheses, dated market evidence, growth experiments, and vetted source contracts |
| Find and evaluate | `opportunity-search`, `opportunity-analysis`, `career-pipeline` | Normalized leads, transparent fit and risk analysis, and event-sourced outcome learning |
| Prepare and apply | `career-materials`, `application-tailoring`, `application-assistance`, `application-campaign` | Evidence-backed baseline materials, truthful role-specific drafts, reviewed forms, and bounded campaigns |
| Communicate and decide | `career-inbox`, `career-networking`, `recruiter-coordination`, `interview-preparation`, `offer-negotiation` | Reconciled messages, grounded outreach, interview practice, and normalized offer comparisons |

Use `career` for a broad or multi-stage request. Invoke a focused skill when
the task already has a clear boundary, such as evaluating one posting,
preparing for one interview, or comparing concrete offer terms.

## Trust Model

- Generated text is not treated as a new fact by itself.
- Material claims are supported, explicitly self-reported, marked for
  confirmation, or omitted.
- Current postings, people, compensation, laws, and platform behavior are
  refreshed and date-stamped when they affect a decision.
- Rankings expose filters, factors, weights, missing data, and freshness. They
  are not presented as probabilities of success.
- Sending, scheduling, submitting, accepting, paying, and deleting require an
  immutable preview, explicit approval for that exact action, and a receipt.
- Sensitive and equal-opportunity attributes are never inferred.

The skills support user decisions; they do not replace legal, tax,
immigration, medical, or mental-health professionals.

## Private Workspace

The helper can create a user-owned career workspace without overwriting an
existing file:

```bash
python scripts/career_core.py init-workspace path/to/career-data
python scripts/career_core.py validate-workspace path/to/career-data
```

Keep this workspace outside the repository and out of version control. Read the
[workspace contract](references/workspace-contract.md) before importing
personal information.

## Deterministic Toolkit

The standard-library-only helper validates records, checks claims, normalizes
and deduplicates opportunities, scores transparent fit factors, projects the
event log, derives an operations brief, and verifies approval-bound effects.

```bash
python scripts/career_core.py --help
python scripts/career_core.py validate-record record.json
python scripts/career_core.py check-triggers
python scripts/token_report.py
```

These commands do not browse, authenticate, send, book, submit, accept, pay, or
delete. Any provider integration remains separate and must satisfy the
[provider contract](references/provider-contract.md).

## Development

The package is network-free at validation time and tested on Windows and Linux
with Python 3.11 and 3.13.

```bash
python scripts/validate_package.py
python -m unittest discover -s tests
python scripts/career_core.py check-triggers
python scripts/token_report.py
```

Read [Contributing](CONTRIBUTING.md) before changing contracts or skills. For
security and privacy reports, follow [Security](SECURITY.md). Career Skills is
available under the [MIT License](LICENSE).
