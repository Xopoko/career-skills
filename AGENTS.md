# Agent Guidance

Career Skills is the canonical public source for an evidence-first career and
job-search skill system. Keep it portable across Codex, Claude Code, Cursor,
and other Agent Skills consumers.

## Repository Role

- This repository owns the plugin source and releases.
- Public metadata, installation, support, and provenance must point only to
  this standalone repository. Private build environments may pin immutable
  revisions without becoming public dependencies.
- Runtime career data is private user state and never belongs in this tree.

## Shape

- `skills/` contains focused Agent Skills; `skills/career/` is the router.
- `references/` contains long contracts, evidence, and playbooks.
- `templates/` contains public-safe synthetic examples.
- `scripts/` contains deterministic, network-free helpers.
- `tests/` contains `unittest` coverage and synthetic fixtures.
- `.codex-plugin/` and `.claude-plugin/` are aligned package manifests.
- The Codex manifest keeps `interface.websiteURL`, `homepage`, and `repository`
  bound to this standalone source.

## Authoring Rules

- Keep repository text in English and ASCII unless exact source data requires
  another character set.
- Never commit resumes, messages, mail, calendar records, employer dossiers,
  credentials, tokens, private names, or other personal data.
- Separate observed facts, user reports, derivations, and inferences.
- Never turn a draft, form fill, proposed slot, or ambiguous provider response
  into a confirmed external outcome.
- External effects require a hash-bound preview, explicit approval, and an
  execution receipt. Preserve append-only history.
- Prefer short skill entrypoints that route to deeper references and scripts.
- Use `$PLUGIN_ROOT` for plugin-owned paths; do not assume a working directory.
- Keep helpers deterministic and standard-library-only unless a dependency is
  explicitly justified, pinned, and documented.

## Change Matrix

When adding, removing, or renaming a skill, update the README skill map, both
manifests, `tests/fixtures/trigger-cases.json`, token reporting, and tests. When
changing a record contract, update its template, reference, validator, and
focused good/bad tests together.

## Validation

Run before committing:

```bash
python scripts/validate_package.py
python -m unittest discover -s tests
python scripts/career_core.py check-triggers
```

For a release, also validate installation from a clean checkout through each
supported host and verify that no ignored runtime data is included.
