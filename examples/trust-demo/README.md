# Synthetic trust demo

This network-free demo exercises the release `0.1.2` trust contracts with
fictional data only. It proves three narrow properties:

1. a resume claim marked `supported` but linked to no active fact is rejected;
2. the same claim passes after a fact and its evidence receipt are linked; and
3. changing one byte in an approved effect payload invalidates its approval
   hash.

Run it from the repository root:

```bash
python scripts/run_trust_demo.py
```

Write the deterministic receipt to a file when another tool needs to inspect
it:

```bash
python scripts/run_trust_demo.py --output tmp/trust-demo-receipt.json
```

The runner invokes the existing commands rather than reimplementing their
logic. Before doing so, it verifies that `scripts/career_core.py` matches the
SHA-256 of the implementation shipped at the named release commit; a later
unreviewed implementation cannot silently inherit the old release receipt.
Repository attributes enforce LF text checkouts. The release-core gate also
normalizes line endings before hashing so an older Windows checkout that
already materialized CRLF cannot fail solely because of newline style.

```bash
python scripts/career_core.py validate-claims --facts examples/trust-demo/facts.jsonl --evidence examples/trust-demo/evidence.jsonl --manifest examples/trust-demo/unsupported-claim-manifest.json --json
python scripts/career_core.py validate-claims --facts examples/trust-demo/facts.jsonl --evidence examples/trust-demo/evidence.jsonl --manifest examples/trust-demo/supported-claim-manifest.json --json
python scripts/career_core.py approval-hash examples/trust-demo/approved-effect-plan.json --as-of 2026-08-13T10:05:00Z --json
```

The first command is expected to exit with status `1`; rejection is the passing
outcome for that scenario. All identifiers, statements, addresses, and results
in this directory are synthetic. They must not be replaced with a real resume,
recruiter message, employer record, or active application data.

Two short public-readable views accompany the machine fixtures:

- [claim-manifest card](claim-manifest-card.md), including sensitivity;
- [application-state card](application-state-card.md), preserving ambiguity.
