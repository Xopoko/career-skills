#!/usr/bin/env python3
"""Validate the standalone Career provider descriptor contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import career_core as core


SCHEMA = "career.provider_descriptor.v1"
MUTABLE_EFFECTS = core.EFFECT_CLASSES - {"network_read", "local_write"}
PAIR_OPERATION_RE = re.compile(
    r"^(plan|execute)(?::([a-z0-9]+(?:-[a-z0-9]+)*))?$"
)
TOP_LEVEL_FIELDS = {
    "schema",
    "provider_id",
    "adapter_version",
    "maintainer",
    "source_revision",
    "license",
    "authentication",
    "network_destinations",
    "redirect_policy",
    "operations",
    "unsupported_filters",
    "freshness",
    "pagination",
    "rate_limits",
    "quota_and_credits",
    "cost",
    "attribution",
    "cache_and_retention",
    "failure_semantics",
    "retry_and_idempotency",
    "activation",
}


def valid_network_destination(destination: str) -> bool:
    """Return whether a destination has a safe, parseable HTTP/WS authority."""
    if any(character.isspace() for character in destination):
        return False
    try:
        parts = urlsplit(destination)
        hostname = parts.hostname
        parts.port
    except (UnicodeError, ValueError):
        return False
    return (
        parts.scheme in {"http", "https", "ws", "wss"}
        and bool(parts.netloc)
        and bool(hostname)
        and parts.username is None
        and parts.password is None
        and not parts.netloc.endswith(":")
    )


def require_object(
    parent: dict[str, Any],
    key: str,
    allowed: set[str],
    record: core.LoadedRecord,
    diagnostics: list[core.Diagnostic],
    code: str,
    base: str = "$",
) -> dict[str, Any]:
    value = parent.get(key)
    path = f"{base}.{key}"
    if not isinstance(value, dict):
        core.diag(
            diagnostics,
            record,
            "error",
            code,
            path,
            f"{key.replace('_', ' ')} object required",
        )
        return {}
    core.reject_unknown(value, allowed, record, diagnostics, path)
    return value


def validate_descriptor(
    record: core.LoadedRecord, diagnostics: list[core.Diagnostic]
) -> None:
    core.walk_numbers(record.value, record, diagnostics)
    value = record.value
    if value.get("schema") != SCHEMA:
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.schema",
            "$.schema",
            f"schema must be {SCHEMA}",
        )
        return
    core.reject_unknown(value, TOP_LEVEL_FIELDS, record, diagnostics)

    provider_id = core.require_string(value, "provider_id", record, diagnostics)
    if provider_id is not None and not core.PROVIDER_ID_RE.fullmatch(provider_id):
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.id",
            "$.provider_id",
            "lowercase kebab-case provider identifier required",
        )
    for key in (
        "adapter_version",
        "maintainer",
        "source_revision",
        "redirect_policy",
        "rate_limits",
        "quota_and_credits",
        "cost",
        "attribution",
        "cache_and_retention",
        "failure_semantics",
    ):
        core.require_string(value, key, record, diagnostics)

    license_info = require_object(
        value,
        "license",
        {"code", "data", "service_terms"},
        record,
        diagnostics,
        "provider.license",
    )
    for key in ("code", "data", "service_terms"):
        core.require_string(license_info, key, record, diagnostics, "$.license")

    authentication = require_object(
        value,
        "authentication",
        {"mode", "secret_boundary"},
        record,
        diagnostics,
        "provider.authentication",
    )
    for key in ("mode", "secret_boundary"):
        core.require_string(
            authentication, key, record, diagnostics, "$.authentication"
        )

    destinations = core.require_string_list(
        value, "network_destinations", record, diagnostics
    )
    for index, destination in enumerate(destinations):
        if not valid_network_destination(destination):
            core.diag(
                diagnostics,
                record,
                "error",
                "provider.network_destination",
                f"$.network_destinations[{index}]",
                "absolute HTTP(S) or WebSocket destination with a valid host and port, no whitespace, and no userinfo required",
            )

    operations = value.get("operations")
    if not isinstance(operations, list) or not operations:
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.operations",
            "$.operations",
            "nonempty operation array required",
        )
        operations = []
    operation_by_name: dict[str, dict[str, Any]] = {}
    pair_operations: dict[
        str | None, dict[str, tuple[dict[str, Any], str]]
    ] = {}
    mutable_operation_paths: set[str] = set()
    for index, operation in enumerate(operations):
        base = f"$.operations[{index}]"
        if not isinstance(operation, dict):
            core.diag(
                diagnostics,
                record,
                "error",
                "provider.operation",
                base,
                "operation object required",
            )
            continue
        core.reject_unknown(
            operation,
            {"name", "effect_class", "data_sent", "data_returned"},
            record,
            diagnostics,
            base,
        )
        name = core.require_string(operation, "name", record, diagnostics, base)
        pair_match = None
        if name is not None:
            if name in operation_by_name:
                core.diag(
                    diagnostics,
                    record,
                    "error",
                    "provider.duplicate_operation",
                    f"{base}.name",
                    "operation names must be unique",
                )
            else:
                operation_by_name[name] = operation
            pair_match = PAIR_OPERATION_RE.fullmatch(name)
            if name.startswith(("plan:", "execute:")) and pair_match is None:
                core.diag(
                    diagnostics,
                    record,
                    "error",
                    "provider.operation_pair_name",
                    f"{base}.name",
                    "qualified plan and execute names require a lowercase kebab-case operation id",
                )
            if pair_match is not None:
                role, operation_id = pair_match.groups()
                pair_operations.setdefault(operation_id, {}).setdefault(
                    role, (operation, base)
                )
        effect_class = operation.get("effect_class")
        if not isinstance(effect_class, str) or effect_class not in core.EFFECT_CLASSES:
            core.diag(
                diagnostics,
                record,
                "error",
                "provider.effect_class",
                f"{base}.effect_class",
                "expected one of: " + ", ".join(sorted(core.EFFECT_CLASSES)),
            )
        elif effect_class in MUTABLE_EFFECTS:
            mutable_operation_paths.add(base)
            if pair_match is None or pair_match.group(1) != "execute":
                core.diag(
                    diagnostics,
                    record,
                    "error",
                    "provider.mutable_operation_unsplit",
                    base,
                    "mutable effects may be exposed only through execute or execute:<operation-id>",
                )
        core.require_string_list(operation, "data_sent", record, diagnostics, base=base)
        core.require_string_list(
            operation, "data_returned", record, diagnostics, base=base
        )

    pairing_invalid = False
    safely_paired_mutable_paths: set[str] = set()
    for operation_id, pair in pair_operations.items():
        plan_entry = pair.get("plan")
        execute_entry = pair.get("execute")
        pair_label = (
            "plan/execute"
            if operation_id is None
            else f"plan:{operation_id}/execute:{operation_id}"
        )
        if plan_entry is None or execute_entry is None:
            pairing_invalid = True
        if plan_entry is not None:
            plan_operation, plan_base = plan_entry
            if plan_operation.get("effect_class") != "local_write":
                core.diag(
                    diagnostics,
                    record,
                    "error",
                    "provider.plan_effect_class",
                    f"{plan_base}.effect_class",
                    f"{pair_label} plan must be a local_write preview operation",
                )
        if execute_entry is not None:
            execute_operation, execute_base = execute_entry
            if execute_operation.get("effect_class") not in MUTABLE_EFFECTS:
                core.diag(
                    diagnostics,
                    record,
                    "error",
                    "provider.execute_effect_class",
                    f"{execute_base}.effect_class",
                    f"{pair_label} execute must declare an external mutable effect class",
                )
            elif (
                plan_entry is not None
                and plan_entry[0].get("effect_class") == "local_write"
            ):
                safely_paired_mutable_paths.add(execute_base)

    if pairing_invalid or mutable_operation_paths != safely_paired_mutable_paths:
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.plan_execute_separation",
            "$.operations",
            "every mutable execute requires its exact local_write plan pair, and plan pairs may not be orphaned",
        )

    core.require_string_list(value, "unsupported_filters", record, diagnostics)
    freshness = require_object(
        value,
        "freshness",
        {"field", "timestamp_unit"},
        record,
        diagnostics,
        "provider.freshness",
    )
    for key in ("field", "timestamp_unit"):
        core.require_string(freshness, key, record, diagnostics, "$.freshness")

    pagination = require_object(
        value,
        "pagination",
        {"model", "partial_results_visible"},
        record,
        diagnostics,
        "provider.pagination",
    )
    core.require_string(pagination, "model", record, diagnostics, "$.pagination")
    if not isinstance(pagination.get("partial_results_visible"), bool):
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.partial_results",
            "$.pagination.partial_results_visible",
            "boolean required",
        )

    retry = require_object(
        value,
        "retry_and_idempotency",
        {"read", "write", "ambiguous_write"},
        record,
        diagnostics,
        "provider.retry_contract",
    )
    read_retry = require_object(
        retry,
        "read",
        {"mode", "max_attempts"},
        record,
        diagnostics,
        "provider.read_retry",
        "$.retry_and_idempotency",
    )
    read_mode = core.require_enum(
        read_retry,
        "mode",
        {"none", "bounded_backoff"},
        record,
        diagnostics,
        "$.retry_and_idempotency.read",
    )
    max_attempts = read_retry.get("max_attempts")
    if (
        isinstance(max_attempts, bool)
        or not isinstance(max_attempts, int)
        or not 1 <= max_attempts <= 10
    ):
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.read_retry_attempts",
            "$.retry_and_idempotency.read.max_attempts",
            "integer from 1 through 10 required",
        )
    elif read_mode == "none" and max_attempts != 1:
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.read_retry_disabled",
            "$.retry_and_idempotency.read.max_attempts",
            "retry mode none requires exactly one attempt",
        )

    write_retry = require_object(
        retry,
        "write",
        {"mode"},
        record,
        diagnostics,
        "provider.write_retry",
        "$.retry_and_idempotency",
    )
    write_mode = core.require_enum(
        write_retry,
        "mode",
        {"not_applicable", "never", "idempotency_key", "remote_state_check"},
        record,
        diagnostics,
        "$.retry_and_idempotency.write",
    )
    ambiguous_write = core.require_enum(
        retry,
        "ambiguous_write",
        {"not_applicable", "stop_and_reconcile"},
        record,
        diagnostics,
        "$.retry_and_idempotency",
    )
    if mutable_operation_paths and write_mode == "not_applicable":
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.mutable_retry_contract",
            "$.retry_and_idempotency.write.mode",
            "mutable providers must prohibit retries or require idempotency or a remote-state check",
        )
    if mutable_operation_paths and ambiguous_write != "stop_and_reconcile":
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.ambiguous_write_contract",
            "$.retry_and_idempotency.ambiguous_write",
            "mutable providers must stop and reconcile ambiguous writes",
        )

    if value.get("activation") != "disabled":
        core.diag(
            diagnostics,
            record,
            "error",
            "provider.activation",
            "$.activation",
            "review descriptors remain disabled until a separate activation decision",
        )


def validate_value(value: dict[str, Any], source: str = "<memory>") -> dict[str, Any]:
    record = core.LoadedRecord(value, source, 1)
    diagnostics: list[core.Diagnostic] = []
    validate_descriptor(record, diagnostics)
    return core.validation_report(diagnostics, [record])


def validate_path(path: Path) -> dict[str, Any]:
    records, diagnostics = core.read_records(path)
    if len(records) != 1:
        placeholder = records[0] if records else core.LoadedRecord({}, path.as_posix(), 0)
        core.diag(
            diagnostics,
            placeholder,
            "error",
            "provider.record_count",
            "$",
            "exactly one provider descriptor is required",
        )
    for record in records:
        validate_descriptor(record, diagnostics)
    return core.validation_report(diagnostics, records)


def cmd_validate(args: argparse.Namespace) -> int:
    report = validate_path(Path(args.descriptor))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        counts = report["counts"]
        state = "PASS" if report["valid"] else "FAIL"
        print(
            f"Provider descriptor validation: {state} "
            f"({counts['records']} records, {counts['errors']} errors, "
            f"{counts['warnings']} warnings)"
        )
        for severity in ("errors", "warnings"):
            for item in report[severity]:
                print(
                    f"{item['severity'].upper()} {item['file']}:{item['line']} "
                    f"{item['json_path']} {item['code']}: {item['message']}"
                )
    return 0 if report["valid"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate one provider descriptor")
    validate.add_argument("descriptor")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
