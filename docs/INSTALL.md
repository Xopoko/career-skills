# Install Career Skills

Career Skills is a repository-root plugin and Agent Skills pack. The skill
files are portable; host-specific installation only changes where the checkout
or links are registered.

## Plug'n Skills

Plug'n Skills can install its reviewed, pinned Career Skills release as a
standalone first-party plugin. Select `career`, or enable standalone plugins by
Xopoko, in the installer. The aggregator pin is immutable and may lag this
repository until its review is refreshed.

## Claude Code

```text
/plugin marketplace add Xopoko/career-skills
/plugin install career@career-skills
```

For the CLI equivalent:

```bash
claude plugin marketplace add Xopoko/career-skills
claude plugin install career@career-skills
```

## Codex and other Agent Skills hosts

Clone the repository to a user-owned plugin or skills directory supported by
the host, then register the repository root or copy/link the individual
directories under `skills/`. Keep `references/`, `templates/`, and `scripts/`
with the skills because workflows resolve them through `$PLUGIN_ROOT`.

```bash
git clone https://github.com/Xopoko/career-skills.git
cd career-skills
python scripts/validate_package.py
python -m unittest discover -s tests
```

Do not run a remote installer blindly. Review the pinned commit and validation
output before enabling any host-provided mail, calendar, browser, or job-source
connector. This repository itself performs no external action.
