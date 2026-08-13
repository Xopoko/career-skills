# Install Career Skills

Career Skills is a repository-root plugin and Agent Skills pack for Codex,
Claude Code, Cursor, and compatible hosts. A correct installation preserves the
complete repository because skills resolve shared references, templates, and
deterministic helpers through the plugin root.

Do not install by copying only individual `skills/` directories. Such a copy
can appear discoverable while failing later when a workflow needs
`references/`, `templates/`, or `scripts/`.

## Before You Install

- Git is required for a local checkout.
- Python 3.11 or newer is required to run the deterministic helpers and local
  validation. The skill text itself has no third-party Python dependency.
- Installing this package does not grant access to mail, calendars, browsers,
  job boards, payment systems, or application forms.

To delegate installation safely, give an agent this complete prompt:

> Install Career Skills from https://github.com/Xopoko/career-skills on this
> computer. Validate the source first, preserve the complete repository so the
> skills can reach their bundled references, templates, and scripts, configure
> it only for the current host, and report exactly what changed. Do not enable
> mail, calendar, browser, or job-source access.

## Codex

Add the GitHub repository as a plugin marketplace, install the `career` plugin,
and inspect the resulting list:

```bash
codex plugin marketplace add Xopoko/career-skills
codex plugin add career@career-skills
codex plugin list
```

To review and validate the source before registering it, use a local checkout:

```bash
git clone https://github.com/Xopoko/career-skills.git
cd career-skills
python scripts/validate_package.py
python -m unittest discover -s tests
codex plugin marketplace add .
codex plugin add career@career-skills
codex plugin list
```

The marketplace name is `career-skills`; the installable plugin name is
`career`.

## Claude Code

Inside an interactive Claude Code session, run:

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

If the plugin was installed during an active session but its skills are not yet
visible, run `/reload-plugins` or start a new session.

## Cursor

Cursor local plugins live under `~/.cursor/plugins/local/`. Keep the complete
Career Skills checkout in one plugin directory.

On macOS or Linux:

```bash
mkdir -p "$HOME/.cursor/plugins/local"
git clone https://github.com/Xopoko/career-skills.git "$HOME/.cursor/plugins/local/career"
cd "$HOME/.cursor/plugins/local/career"
python3 scripts/validate_package.py
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME/.cursor/plugins/local" | Out-Null
git clone https://github.com/Xopoko/career-skills.git "$HOME/.cursor/plugins/local/career"
Set-Location "$HOME/.cursor/plugins/local/career"
python scripts/validate_package.py
```

Restart Cursor or run **Developer: Reload Window**. Open **Customize** and
confirm that **Career Skills** is present. If the skills appear but shared
references cannot be opened, remove the partial copy and reinstall the complete
repository at the path above.

## Plug'n Skills

[Plug'n Skills](https://github.com/Xopoko/plug-n-skills) can install a reviewed,
immutable Career Skills revision through its Codex installer. Select `career`
when using that installer. The reviewed pin may intentionally lag this
repository while a new revision is audited.

Use this standalone repository when you want the newest Career Skills source.
Use the aggregator when you want one installer and a reviewed set of plugins.

## Validate a Checkout

From the repository root, run:

```bash
python scripts/validate_package.py
python -m unittest discover -s tests
python scripts/career_core.py check-triggers
python scripts/token_report.py
```

The first command checks the package layout, manifests, skill metadata,
references, templates, and public-safety rules. The tests exercise the record,
workspace, campaign, pipeline, approval, and projection contracts. The trigger
check validates corpus coverage and structure for every skill's positive and
negative routing examples.

If your system exposes Python as `python3`, substitute `python3` in the commands
above.

## Connector and Action Boundary

Career Skills ships no live job-board, mail, calendar, browser, payment, or
submission connector. A host may provide those tools separately, but install
them and grant access only when the user has selected the provider and scope.

Even with a connector available, drafting and executing remain separate.
External effects require a hash-bound preview, explicit approval for the exact
action, and an execution receipt. See the
[provider contract](../references/provider-contract.md) and
[application and effects contract](../references/application-and-effects.md).

## Troubleshooting

- **The plugin is not listed:** confirm the marketplace registration, then
  restart or reload the host and run its list command again.
- **A skill cannot open a bundled file:** the plugin root is incomplete. Reinstall
  the full repository instead of copying an individual skill.
- **Local validation cannot find Python:** install Python 3.11 or newer, or try
  `python3` instead of `python`.
- **A connector is unavailable:** this package does not supply connectors. The
  host integration must be installed and authorized separately.
