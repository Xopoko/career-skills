#!/usr/bin/env python3
"""Report deterministic approximate token budgets for Career Skills."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def estimate(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text, re.UNICODE))


def main() -> int:
    rows = []
    for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        parts = text.split("---\n", 2)
        metadata = parts[1] if len(parts) == 3 else ""
        body = parts[2] if len(parts) == 3 else text
        rows.append(
            {
                "name": path.parent.name,
                "startup_tokens": estimate(metadata),
                "body_tokens": estimate(body),
            }
        )
    report = {
        "schema": "career.token_report.v1",
        "skills": rows,
        "totals": {
            "skills": len(rows),
            "startup_tokens": sum(item["startup_tokens"] for item in rows),
            "body_tokens": sum(item["body_tokens"] for item in rows),
        },
        "note": "Regex estimate for regression tracking; not a provider tokenizer.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
