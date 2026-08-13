#!/usr/bin/env python3
"""Run the public synthetic trust demo through the existing Career Skills CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "scripts" / "career_core.py"
FIXTURES = ROOT / "examples" / "trust-demo"
RELEASE_COMMIT = "42e77fbe5592f1953e6407784bba024e6956f2e7"
RELEASE_CORE_SHA256 = "eed979cda30ea7788c1772b222d78d1f200bb40a022df36f34cbe705de841a41"
AS_OF = "2026-08-13T10:05:00Z"


class DemoError(RuntimeError):
    """Raised when the underlying command does not return its JSON contract."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_text_sha256(path: Path) -> str:
    payload = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(payload).hexdigest()


def stable_command(arguments: Sequence[str]) -> str:
    return "python scripts/career_core.py " + " ".join(arguments)


def run_core(arguments: Sequence[str]) -> tuple[int, dict[str, Any]]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(CORE), *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DemoError(
            f"career_core.py returned non-JSON output with exit {completed.returncode}"
        ) from exc
    if not isinstance(payload, dict):
        raise DemoError("career_core.py returned a non-object JSON value")
    return completed.returncode, payload


def error_codes(payload: dict[str, Any]) -> list[str]:
    return sorted(
        item["code"]
        for item in payload.get("errors", [])
        if isinstance(item, dict) and isinstance(item.get("code"), str)
    )


def claim_arguments(manifest: str) -> list[str]:
    return [
        "validate-claims",
        "--facts",
        "examples/trust-demo/facts.jsonl",
        "--evidence",
        "examples/trust-demo/evidence.jsonl",
        "--manifest",
        f"examples/trust-demo/{manifest}",
        "--json",
    ]


def build_receipt() -> dict[str, Any]:
    core_sha256 = normalized_text_sha256(CORE)
    if core_sha256 != RELEASE_CORE_SHA256:
        raise DemoError(
            "career_core.py does not match the release-bound trust-demo contract"
        )
    unsupported_args = claim_arguments("unsupported-claim-manifest.json")
    unsupported_exit, unsupported = run_core(unsupported_args)
    unsupported_codes = error_codes(unsupported)
    unsupported_passed = (
        unsupported_exit == 1
        and unsupported.get("valid") is False
        and "claim.unsupported" in unsupported_codes
    )

    supported_args = claim_arguments("supported-claim-manifest.json")
    supported_exit, supported = run_core(supported_args)
    supported_passed = (
        supported_exit == 0
        and supported.get("valid") is True
        and not error_codes(supported)
    )

    approval_args = [
        "approval-hash",
        "examples/trust-demo/approved-effect-plan.json",
        "--as-of",
        AS_OF,
        "--json",
    ]
    approval_exit, approval = run_core(approval_args)
    approval_passed = (
        approval_exit == 0
        and approval.get("valid") is True
        and approval.get("executable") is True
        and approval.get("expected_hash") == approval.get("supplied_hash")
    )

    source_plan = FIXTURES / "approved-effect-plan.json"
    source_bytes = source_plan.read_bytes()
    needle = b'Reviewed message body.'
    replacement = b'Reviewed message body!'
    if source_bytes.count(needle) != 1 or len(needle) != len(replacement):
        raise DemoError("approved plan no longer contains the one-byte mutation target")
    mutated_bytes = source_bytes.replace(needle, replacement, 1)
    byte_diff_count = sum(left != right for left, right in zip(source_bytes, mutated_bytes))
    byte_diff_count += abs(len(source_bytes) - len(mutated_bytes))

    with tempfile.TemporaryDirectory(prefix="career-trust-demo-") as temporary:
        mutated_path = Path(temporary) / "approved-effect-plan-mutated.json"
        mutated_path.write_bytes(mutated_bytes)
        mutation_args_runtime = [
            "approval-hash",
            str(mutated_path),
            "--as-of",
            AS_OF,
            "--json",
        ]
        mutation_exit, mutation = run_core(mutation_args_runtime)

    mutation_codes = error_codes(mutation)
    mutation_passed = (
        byte_diff_count == 1
        and mutation_exit == 1
        and mutation.get("valid") is False
        and mutation.get("executable") is False
        and mutation.get("expected_hash") != mutation.get("supplied_hash")
        and "plan.approval_hash_mismatch" in mutation_codes
    )
    mutation_args_display = [
        "approval-hash",
        "<temporary-one-byte-mutated-plan.json>",
        "--as-of",
        AS_OF,
        "--json",
    ]

    scenarios = [
        {
            "actual_exit": unsupported_exit,
            "command": stable_command(unsupported_args),
            "error_codes": unsupported_codes,
            "expected_exit": 1,
            "id": "unsupported_claim_rejected",
            "passed": unsupported_passed,
            "valid": unsupported.get("valid"),
        },
        {
            "actual_exit": supported_exit,
            "command": stable_command(supported_args),
            "error_codes": error_codes(supported),
            "expected_exit": 0,
            "id": "supported_claim_accepted",
            "passed": supported_passed,
            "valid": supported.get("valid"),
        },
        {
            "actual_exit": approval_exit,
            "command": stable_command(approval_args),
            "executable": approval.get("executable"),
            "expected_exit": 0,
            "expected_hash": approval.get("expected_hash"),
            "id": "approved_payload_hash_valid",
            "passed": approval_passed,
            "supplied_hash": approval.get("supplied_hash"),
            "valid": approval.get("valid"),
        },
        {
            "actual_exit": mutation_exit,
            "byte_diff_count": byte_diff_count,
            "command": stable_command(mutation_args_display),
            "error_codes": mutation_codes,
            "expected_exit": 1,
            "expected_hash": mutation.get("expected_hash"),
            "id": "one_byte_payload_mutation_rejected",
            "passed": mutation_passed,
            "supplied_hash": mutation.get("supplied_hash"),
            "valid": mutation.get("valid"),
        },
    ]
    passed_count = sum(bool(item["passed"]) for item in scenarios)
    fixture_names = (
        "approved-effect-plan.json",
        "evidence.jsonl",
        "facts.jsonl",
        "supported-claim-manifest.json",
        "unsupported-claim-manifest.json",
    )
    return {
        "as_of": AS_OF,
        "contract_release_commit": RELEASE_COMMIT,
        "contract_core_sha256": core_sha256,
        "demo_id": "career-trust-demo-v1",
        "fixture_sha256": {
            name: sha256(FIXTURES / name) for name in fixture_names
        },
        "scenarios": scenarios,
        "schema": "career.trust_demo_receipt.v1",
        "summary": {
            "passed": passed_count,
            "total": len(scenarios),
            "valid": passed_count == len(scenarios),
        },
        "synthetic_data_only": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Career Skills synthetic trust demo."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON receipt. The same receipt is printed to stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        receipt = build_receipt()
    except DemoError as exc:
        print(f"trust demo failed: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    sys.stdout.write(rendered)
    return 0 if receipt["summary"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
