#!/usr/bin/env python3
"""Validate and operate the local, provider-neutral Career data contracts."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SAFE_INTEGER = 2**53 - 1
UUID_PART = r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROVIDER_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PREDICATE_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

FACT_SCHEMA = "career.fact.v1"
EVIDENCE_SCHEMA = "career.evidence_receipt.v1"
OPPORTUNITY_SCHEMA = "career.opportunity.v1"
EVENT_SCHEMA = "career.pipeline_event.v1"
PLAN_SCHEMA = "career.effect_plan.v1"
PROFILE_SCHEMA = "career.profile.v1"
SEARCH_POLICY_SCHEMA = "career.search_policy.v1"
ARTIFACT_SCHEMA = "career.artifact_receipt.v1"
CAMPAIGN_SCHEMA = "career.application_campaign.v1"
ACTION_SCHEMA = "career.action.v1"
CORE_SCHEMAS = {
    FACT_SCHEMA,
    EVIDENCE_SCHEMA,
    OPPORTUNITY_SCHEMA,
    EVENT_SCHEMA,
    PLAN_SCHEMA,
    PROFILE_SCHEMA,
    SEARCH_POLICY_SCHEMA,
    ARTIFACT_SCHEMA,
    CAMPAIGN_SCHEMA,
    ACTION_SCHEMA,
}

LEDGER_SCHEMAS = {
    "facts.jsonl": FACT_SCHEMA,
    "evidence.jsonl": EVIDENCE_SCHEMA,
    "opportunities.jsonl": OPPORTUNITY_SCHEMA,
    "pipeline-events.jsonl": EVENT_SCHEMA,
    "actions.jsonl": ACTION_SCHEMA,
}

WORKSPACE_SINGLE_SCHEMAS = {
    "profile.json": PROFILE_SCHEMA,
    "search-policy.json": SEARCH_POLICY_SCHEMA,
}

WORKSPACE_NESTED_LEDGERS = {
    "artifacts/index.jsonl": ARTIFACT_SCHEMA,
}

STAGES = (
    "discovered",
    "considering",
    "preparing",
    "applied",
    "screening",
    "interviewing",
    "offer",
    "closed",
)
OUTCOMES = {
    "hired",
    "rejected",
    "withdrawn",
    "offer_declined",
    "role_closed",
    "expired",
    "duplicate",
    "no_response",
    "other",
}
EVENT_TYPES = {
    "discovered",
    "review_started",
    "shortlisted",
    "preparation_started",
    "application_ready",
    "application_submitted",
    "recruiter_contact",
    "recruiter_chat_proposed",
    "recruiter_chat_scheduled",
    "recruiter_chat_completed",
    "interview_proposed",
    "interview_scheduled",
    "interview_completed",
    "offer_received",
    "outcome_recorded",
    "artifact_linked",
    "follow_up_due",
    "note",
    "correction",
    "reopened",
    "effect_executed",
    "effect_reconciled",
}
EFFECT_CLASSES = {
    "network_read",
    "local_write",
    "remote_write",
    "communication",
    "application_submission",
    "payment",
    "delete",
}


class StrictJSONError(ValueError):
    """Raised for duplicate keys or non-finite JSON constants."""


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    file: str
    line: int
    json_path: str
    message: str


@dataclass(frozen=True)
class LoadedRecord:
    value: dict[str, Any]
    file: str
    line: int


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-finite number is not valid: {value}")


def strict_json_loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_constant,
    )


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not RFC3339_RE.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def typed_uuid(value: Any, prefix: str) -> bool:
    return isinstance(value, str) and re.fullmatch(
        rf"{re.escape(prefix)}-{UUID_PART}", value
    ) is not None


def diag(
    diagnostics: list[Diagnostic],
    record: LoadedRecord,
    severity: str,
    code: str,
    json_path: str,
    message: str,
) -> None:
    diagnostics.append(
        Diagnostic(severity, code, record.file, record.line, json_path, message)
    )


def read_records(path: Path) -> tuple[list[LoadedRecord], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    records: list[LoadedRecord] = []
    rel = path.as_posix()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        placeholder = LoadedRecord({}, rel, 0)
        diag(diagnostics, placeholder, "error", "io.read", "$", str(exc))
        return records, diagnostics

    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig" if bom else "utf-8")
    except UnicodeDecodeError as exc:
        placeholder = LoadedRecord({}, rel, 0)
        diag(diagnostics, placeholder, "error", "json.encoding", "$", str(exc))
        return records, diagnostics

    placeholder = LoadedRecord({}, rel, 1)
    if bom:
        diag(
            diagnostics,
            placeholder,
            "warning",
            "json.bom",
            "$",
            "UTF-8 BOM accepted; write plain UTF-8 for stable diffs",
        )
    if raw and not raw.endswith((b"\n", b"\r")):
        diag(
            diagnostics,
            placeholder,
            "warning",
            "json.missing_final_newline",
            "$",
            "file does not end with a newline",
        )

    if path.suffix.lower() == ".jsonl":
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                value = strict_json_loads(line)
            except (json.JSONDecodeError, StrictJSONError) as exc:
                record = LoadedRecord({}, rel, line_no)
                diag(
                    diagnostics,
                    record,
                    "error",
                    "json.parse",
                    "$",
                    f"invalid one-object JSONL line: {exc}",
                )
                continue
            if not isinstance(value, dict):
                record = LoadedRecord({}, rel, line_no)
                diag(
                    diagnostics,
                    record,
                    "error",
                    "json.object_required",
                    "$",
                    "each nonblank JSONL line must be one object",
                )
                continue
            records.append(LoadedRecord(value, rel, line_no))
        return records, diagnostics

    try:
        value = strict_json_loads(text)
    except (json.JSONDecodeError, StrictJSONError) as exc:
        diag(diagnostics, placeholder, "error", "json.parse", "$", str(exc))
        return records, diagnostics
    values = value if isinstance(value, list) else [value]
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            record = LoadedRecord({}, rel, index + 1)
            diag(
                diagnostics,
                record,
                "error",
                "json.object_required",
                f"$[{index}]",
                "JSON records must be objects",
            )
            continue
        records.append(LoadedRecord(item, rel, index + 1))
    return records, diagnostics


def walk_numbers(
    value: Any,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    json_path: str = "$",
) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, float):
        diag(
            diagnostics,
            record,
            "error",
            "json.float_forbidden",
            json_path,
            "use an integer or a decimal string; binary floats are forbidden",
        )
        return
    if isinstance(value, int):
        if abs(value) > SAFE_INTEGER:
            diag(
                diagnostics,
                record,
                "error",
                "json.unsafe_integer",
                json_path,
                f"integer exceeds the interoperable limit {SAFE_INTEGER}",
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            walk_numbers(item, record, diagnostics, f"{json_path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            walk_numbers(item, record, diagnostics, f"{json_path}.{key}")


def require_string(
    obj: dict[str, Any],
    key: str,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    base: str = "$",
) -> str | None:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        diag(
            diagnostics,
            record,
            "error",
            "field.string_required",
            f"{base}.{key}",
            "nonempty string required",
        )
        return None
    return value


def require_time(
    obj: dict[str, Any],
    key: str,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    base: str = "$",
) -> datetime | None:
    value = obj.get(key)
    parsed = parse_time(value)
    if parsed is None:
        diag(
            diagnostics,
            record,
            "error",
            "field.rfc3339_required",
            f"{base}.{key}",
            "RFC 3339 timestamp with Z or numeric offset required",
        )
    return parsed


def require_typed_uuid(
    obj: dict[str, Any],
    key: str,
    prefix: str,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    base: str = "$",
) -> str | None:
    value = obj.get(key)
    if not typed_uuid(value, prefix):
        diag(
            diagnostics,
            record,
            "error",
            "field.typed_uuid_required",
            f"{base}.{key}",
            f"canonical {prefix}-<uuid> identifier required",
        )
        return None
    return value


def require_enum(
    obj: dict[str, Any],
    key: str,
    allowed: set[str],
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    base: str = "$",
) -> str | None:
    value = obj.get(key)
    if not isinstance(value, str) or value not in allowed:
        diag(
            diagnostics,
            record,
            "error",
            "field.enum",
            f"{base}.{key}",
            "expected one of: " + ", ".join(sorted(allowed)),
        )
        return None
    return value


def reject_unknown(
    obj: dict[str, Any],
    allowed: set[str],
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    base: str = "$",
) -> None:
    for key in sorted(set(obj) - allowed):
        diag(
            diagnostics,
            record,
            "error",
            "field.unknown",
            f"{base}.{key}",
            "unknown field",
        )


def require_id_list(
    obj: dict[str, Any],
    key: str,
    prefix: str,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    *,
    nonempty: bool = False,
    base: str = "$",
) -> list[str]:
    value = obj.get(key)
    if not isinstance(value, list) or (nonempty and not value):
        diag(
            diagnostics,
            record,
            "error",
            "field.id_list",
            f"{base}.{key}",
            "identifier array required" + (" and must not be empty" if nonempty else ""),
        )
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not typed_uuid(item, prefix):
            diag(
                diagnostics,
                record,
                "error",
                "field.typed_uuid_required",
                f"{base}.{key}[{index}]",
                f"canonical {prefix}-<uuid> identifier required",
            )
            continue
        result.append(item)
    if len(result) != len(set(result)):
        diag(
            diagnostics,
            record,
            "error",
            "field.duplicate_list_member",
            f"{base}.{key}",
            "duplicate identifiers are not allowed",
        )
    return result


def validate_relative_locator(
    value: str,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    json_path: str,
) -> None:
    windows = PureWindowsPath(value)
    posix = PurePosixPath(value.replace("\\", "/"))
    if (
        windows.is_absolute()
        or bool(windows.drive)
        or value.startswith(("\\\\", "//", "/"))
        or ".." in posix.parts
    ):
        diag(
            diagnostics,
            record,
            "error",
            "evidence.unsafe_locator",
            json_path,
            "file locator must be relative to the Career workspace without traversal",
        )


def require_string_list(
    obj: dict[str, Any],
    key: str,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    *,
    nonempty: bool = False,
    base: str = "$",
) -> list[str]:
    value = obj.get(key)
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        diag(
            diagnostics,
            record,
            "error",
            "field.string_list",
            f"{base}.{key}",
            "nonempty-string array required"
            + (" and must not be empty" if nonempty else ""),
        )
        return []
    if len(value) != len(set(value)):
        diag(
            diagnostics,
            record,
            "error",
            "field.duplicate_list_member",
            f"{base}.{key}",
            "duplicate values are not allowed",
        )
    return value


def optional_time(
    obj: dict[str, Any],
    key: str,
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    base: str = "$",
) -> datetime | None:
    if obj.get(key) is None:
        return None
    return require_time(obj, key, record, diagnostics, base)


def validate_profile(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {"schema", "subject_id", "created_at", "goals", "preferences", "constraints", "retention", "sharing"},
        record,
        diagnostics,
    )
    require_typed_uuid(value, "subject_id", "subject", record, diagnostics)
    require_time(value, "created_at", record, diagnostics)
    goals = value.get("goals")
    if not isinstance(goals, list):
        diag(diagnostics, record, "error", "profile.goals", "$.goals", "array required")
        goals = []
    for index, goal in enumerate(goals):
        base = f"$.goals[{index}]"
        if not isinstance(goal, dict):
            diag(diagnostics, record, "error", "profile.goal", base, "object required")
            continue
        reject_unknown(goal, {"outcome", "horizon", "status"}, record, diagnostics, base)
        require_string(goal, "outcome", record, diagnostics, base)
        require_enum(
            goal,
            "horizon",
            {"immediate", "next_role", "one_year", "long_term", "other"},
            record,
            diagnostics,
            base,
        )
        require_enum(
            goal,
            "status",
            {"exploring", "active", "paused", "achieved", "retired"},
            record,
            diagnostics,
            base,
        )
    preferences = value.get("preferences")
    if not isinstance(preferences, dict):
        diag(diagnostics, record, "error", "profile.preferences", "$.preferences", "object required")
        preferences = {}
    reject_unknown(
        preferences,
        {"role_families", "workplace", "locations", "timezones", "employment_types"},
        record,
        diagnostics,
        "$.preferences",
    )
    for key in ("role_families", "workplace", "locations", "timezones", "employment_types"):
        require_string_list(preferences, key, record, diagnostics, base="$.preferences")
    constraints = value.get("constraints")
    if not isinstance(constraints, dict):
        diag(diagnostics, record, "error", "profile.constraints", "$.constraints", "object required")
        constraints = {}
    reject_unknown(constraints, {"hard", "soft", "unknown"}, record, diagnostics, "$.constraints")
    for key in ("hard", "soft", "unknown"):
        require_string_list(constraints, key, record, diagnostics, base="$.constraints")
    retention = value.get("retention")
    if not isinstance(retention, dict):
        diag(diagnostics, record, "error", "profile.retention", "$.retention", "object required")
        retention = {}
    reject_unknown(
        retention,
        {"default_days", "keep_evidence_until_review", "review_on"},
        record,
        diagnostics,
        "$.retention",
    )
    days = retention.get("default_days")
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650:
        diag(diagnostics, record, "error", "profile.retention_days", "$.retention.default_days", "integer from 1 to 3650 required")
    if not isinstance(retention.get("keep_evidence_until_review"), bool):
        diag(diagnostics, record, "error", "profile.retention_flag", "$.retention.keep_evidence_until_review", "boolean required")
    optional_time(retention, "review_on", record, diagnostics, "$.retention")
    sharing = value.get("sharing")
    if not isinstance(sharing, dict):
        diag(diagnostics, record, "error", "profile.sharing", "$.sharing", "object required")
        sharing = {}
    reject_unknown(sharing, {"default"}, record, diagnostics, "$.sharing")
    require_enum(
        sharing,
        "default",
        {"local_only", "approved_exports_only"},
        record,
        diagnostics,
        "$.sharing",
    )


def validate_search_policy(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema", "subject_id", "updated_at", "role_families", "adjacent_titles",
            "hard_filters", "positive_signals", "avoid_signals", "authorized_sources",
            "source_queries", "freshness_days", "review_cadence_days", "result_budget_per_run",
        },
        record,
        diagnostics,
    )
    require_typed_uuid(value, "subject_id", "subject", record, diagnostics)
    require_time(value, "updated_at", record, diagnostics)
    for key in (
        "role_families", "adjacent_titles", "hard_filters", "positive_signals",
        "avoid_signals", "authorized_sources", "source_queries",
    ):
        require_string_list(value, key, record, diagnostics)
    for key, minimum, maximum in (
        ("freshness_days", 1, 365),
        ("review_cadence_days", 1, 365),
        ("result_budget_per_run", 1, 1000),
    ):
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, int) or not minimum <= item <= maximum:
            diag(diagnostics, record, "error", "search_policy.integer", f"$.{key}", f"integer from {minimum} to {maximum} required")


def validate_artifact(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema", "artifact_id", "revision_id", "supersedes_revision_id", "recorded_at",
            "kind", "relative_path", "sha256", "media_type", "opportunity_id", "status",
            "source_fact_ids", "evidence_ids", "derived_from_artifact_ids", "claim_manifest_path",
        },
        record,
        diagnostics,
    )
    artifact_id = require_typed_uuid(value, "artifact_id", "artifact", record, diagnostics)
    revision_id = require_typed_uuid(value, "revision_id", "artifact-revision", record, diagnostics)
    supersedes = value.get("supersedes_revision_id")
    if supersedes is not None and not typed_uuid(supersedes, "artifact-revision"):
        diag(diagnostics, record, "error", "field.typed_uuid_required", "$.supersedes_revision_id", "null or canonical artifact-revision-<uuid> required")
    if revision_id is not None and supersedes == revision_id:
        diag(diagnostics, record, "error", "revision.self_reference", "$.supersedes_revision_id", "revision cannot supersede itself")
    require_time(value, "recorded_at", record, diagnostics)
    require_enum(
        value,
        "kind",
        {"resume", "cover_letter", "portfolio", "profile", "message", "interview_notes", "offer_analysis", "review_packet", "other"},
        record,
        diagnostics,
    )
    locator = require_string(value, "relative_path", record, diagnostics)
    if locator is not None:
        validate_relative_locator(locator, record, diagnostics, "$.relative_path")
    sha = value.get("sha256")
    if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
        diag(diagnostics, record, "error", "artifact.sha256", "$.sha256", "lowercase SHA-256 required")
    require_string(value, "media_type", record, diagnostics)
    opportunity_id = value.get("opportunity_id")
    if opportunity_id is not None and not typed_uuid(opportunity_id, "opportunity"):
        diag(diagnostics, record, "error", "field.typed_uuid_required", "$.opportunity_id", "null or canonical opportunity-<uuid> required")
    require_enum(value, "status", {"draft", "reviewed", "final", "submitted", "superseded"}, record, diagnostics)
    require_id_list(value, "source_fact_ids", "fact", record, diagnostics)
    require_id_list(value, "evidence_ids", "evidence", record, diagnostics)
    derived = require_id_list(value, "derived_from_artifact_ids", "artifact", record, diagnostics)
    if artifact_id is not None and artifact_id in derived:
        diag(diagnostics, record, "error", "artifact.self_derivation", "$.derived_from_artifact_ids", "artifact cannot derive from itself")
    manifest = value.get("claim_manifest_path")
    if manifest is not None:
        if not isinstance(manifest, str) or not manifest:
            diag(diagnostics, record, "error", "artifact.claim_manifest_path", "$.claim_manifest_path", "relative string or null required")
        else:
            validate_relative_locator(manifest, record, diagnostics, "$.claim_manifest_path")


def validate_campaign(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema", "campaign_id", "revision_id", "supersedes_revision_id",
            "recorded_at", "name", "owner", "purpose", "deadline_at",
            "maximum_attempts", "source_policy", "allowed_account_ids",
            "review_cadence", "stop_conditions", "workspace_tail", "state",
            "target_count", "roster_count", "reserve_count", "items", "counts",
        },
        record,
        diagnostics,
    )
    require_typed_uuid(value, "campaign_id", "campaign", record, diagnostics)
    revision_id = require_typed_uuid(value, "revision_id", "campaign-revision", record, diagnostics)
    supersedes = value.get("supersedes_revision_id")
    if supersedes is not None and not typed_uuid(supersedes, "campaign-revision"):
        diag(diagnostics, record, "error", "field.typed_uuid_required", "$.supersedes_revision_id", "null or canonical campaign-revision-<uuid> required")
    if revision_id is not None and revision_id == supersedes:
        diag(diagnostics, record, "error", "revision.self_reference", "$.supersedes_revision_id", "revision cannot supersede itself")
    recorded_at = require_time(value, "recorded_at", record, diagnostics)
    require_string(value, "name", record, diagnostics)
    owner = value.get("owner")
    if not isinstance(owner, dict):
        diag(diagnostics, record, "error", "campaign.owner", "$.owner", "owner object required")
        owner = {}
    reject_unknown(owner, {"kind", "id"}, record, diagnostics, "$.owner")
    require_enum(owner, "kind", {"user", "agent", "team"}, record, diagnostics, "$.owner")
    if owner.get("id") is not None:
        require_string(owner, "id", record, diagnostics, "$.owner")
    require_string(value, "purpose", record, diagnostics)
    deadline_at = require_time(value, "deadline_at", record, diagnostics)
    if recorded_at is not None and deadline_at is not None and deadline_at <= recorded_at:
        diag(diagnostics, record, "error", "campaign.deadline_order", "$.deadline_at", "deadline must follow the campaign revision time")
    maximum_attempts = value.get("maximum_attempts")
    if isinstance(maximum_attempts, bool) or not isinstance(maximum_attempts, int) or maximum_attempts < 1:
        diag(diagnostics, record, "error", "campaign.maximum_attempts", "$.maximum_attempts", "positive integer required")
    source_policy = value.get("source_policy")
    if not isinstance(source_policy, dict):
        diag(diagnostics, record, "error", "campaign.source_policy", "$.source_policy", "source policy object required")
        source_policy = {}
    reject_unknown(source_policy, {"allowed_provider_ids", "allowed_domains", "eligibility_rule"}, record, diagnostics, "$.source_policy")
    provider_ids = require_string_list(source_policy, "allowed_provider_ids", record, diagnostics, base="$.source_policy")
    for index, provider_id in enumerate(provider_ids):
        if not PROVIDER_ID_RE.fullmatch(provider_id):
            diag(diagnostics, record, "error", "provider.id", f"$.source_policy.allowed_provider_ids[{index}]", "lowercase kebab-case provider identifier required")
    domains = require_string_list(source_policy, "allowed_domains", record, diagnostics, base="$.source_policy")
    if not provider_ids and not domains:
        diag(diagnostics, record, "error", "campaign.empty_source_policy", "$.source_policy", "at least one allowed provider or domain is required")
    require_string(source_policy, "eligibility_rule", record, diagnostics, "$.source_policy")
    require_string_list(value, "allowed_account_ids", record, diagnostics, nonempty=True)
    require_enum(value, "review_cadence", {"after_each_attempt", "daily", "manual_checkpoint"}, record, diagnostics)
    stop_conditions = require_string_list(value, "stop_conditions", record, diagnostics, nonempty=True)
    known_stops = {
        "quota_reached", "approval_scope_changed", "workspace_tail_changed",
        "account_uncertain", "provider_changed", "cost_or_terms_appeared",
        "truth_missing", "artifact_qa_failed", "duplicate_risk",
        "reconciliation_failed", "deadline_reached", "attempt_limit_reached",
    }
    for index, condition in enumerate(stop_conditions):
        if condition not in known_stops:
            diag(diagnostics, record, "error", "campaign.stop_condition", f"$.stop_conditions[{index}]", "unknown stop condition")
    workspace_tail = value.get("workspace_tail")
    if not isinstance(workspace_tail, dict):
        diag(diagnostics, record, "error", "campaign.workspace_tail", "$.workspace_tail", "workspace tail object required")
        workspace_tail = {}
    reject_unknown(
        workspace_tail,
        {
            "captured_at", "profile_subject_id", "search_policy_subject_id",
            "opportunity_revision_ids", "pipeline_tail_event_ids", "artifact_revision_ids",
        },
        record,
        diagnostics,
        "$.workspace_tail",
    )
    captured_at = require_time(workspace_tail, "captured_at", record, diagnostics, "$.workspace_tail")
    if recorded_at is not None and captured_at is not None and captured_at > recorded_at:
        diag(diagnostics, record, "error", "campaign.future_workspace_tail", "$.workspace_tail.captured_at", "workspace tail cannot be captured after the campaign revision")
    require_typed_uuid(workspace_tail, "profile_subject_id", "subject", record, diagnostics, "$.workspace_tail")
    require_typed_uuid(workspace_tail, "search_policy_subject_id", "subject", record, diagnostics, "$.workspace_tail")
    require_id_list(workspace_tail, "opportunity_revision_ids", "opportunity-revision", record, diagnostics, nonempty=True, base="$.workspace_tail")
    require_id_list(workspace_tail, "pipeline_tail_event_ids", "event", record, diagnostics, base="$.workspace_tail")
    require_id_list(workspace_tail, "artifact_revision_ids", "artifact-revision", record, diagnostics, base="$.workspace_tail")
    require_enum(value, "state", {"draft", "ready", "running", "paused", "completed", "cancelled"}, record, diagnostics)
    target_count = value.get("target_count")
    if isinstance(target_count, bool) or not isinstance(target_count, int) or target_count < 1:
        diag(diagnostics, record, "error", "campaign.target_count", "$.target_count", "positive integer required")
    roster_count = value.get("roster_count")
    if isinstance(roster_count, bool) or not isinstance(roster_count, int) or roster_count < 1:
        diag(diagnostics, record, "error", "campaign.roster_count", "$.roster_count", "positive integer required")
    reserve_count = value.get("reserve_count")
    if isinstance(reserve_count, bool) or not isinstance(reserve_count, int) or reserve_count < 0:
        diag(diagnostics, record, "error", "campaign.reserve_count", "$.reserve_count", "nonnegative integer required")
    items = value.get("items")
    if not isinstance(items, list) or not items:
        diag(diagnostics, record, "error", "campaign.items", "$.items", "nonempty item array required")
        items = []
    opportunity_ids: list[str] = []
    item_ids: list[str] = []
    slot_ids: list[str] = []
    primary_count = 0
    observed_reserves = 0
    replacement_targets: list[tuple[str, str | None, str | None]] = []
    observed = Counter()
    attempted_states = {"succeeded", "failed", "ambiguous", "denied", "cancelled"}
    for index, item in enumerate(items):
        base = f"$.items[{index}]"
        if not isinstance(item, dict):
            diag(diagnostics, record, "error", "campaign.item", base, "object required")
            continue
        reject_unknown(
            item,
            {
                "item_id", "slot_id", "cohort_role", "replacement_of", "activation_reason",
                "opportunity_id", "opportunity_revision_id", "canonical_url", "organization",
                "title", "freshness_evidence_id", "eligibility", "fit_decision", "priority",
                "dependency_action_ids", "artifact_revision_ids", "plan_id", "plan_revision_id",
                "approval_hash", "state", "attempted_at", "effect_event_id", "failure_reason",
            },
            record,
            diagnostics,
            base,
        )
        item_id = require_typed_uuid(item, "item_id", "campaign-item", record, diagnostics, base)
        if item_id is not None:
            item_ids.append(item_id)
        slot_id = require_string(item, "slot_id", record, diagnostics, base)
        if slot_id is not None:
            slot_ids.append(slot_id)
        cohort_role = require_enum(item, "cohort_role", {"primary", "reserve", "replacement"}, record, diagnostics, base)
        if cohort_role == "primary":
            primary_count += 1
        elif cohort_role == "reserve":
            observed_reserves += 1
        replacement_of = item.get("replacement_of")
        if replacement_of is not None and not typed_uuid(replacement_of, "campaign-item"):
            diag(diagnostics, record, "error", "field.typed_uuid_required", f"{base}.replacement_of", "null or canonical campaign-item-<uuid> required")
        if cohort_role == "replacement" and replacement_of is None:
            diag(diagnostics, record, "error", "campaign.replacement_target", f"{base}.replacement_of", "replacement items must identify the item they replace")
        if cohort_role != "replacement" and replacement_of is not None:
            diag(diagnostics, record, "error", "campaign.unexpected_replacement", f"{base}.replacement_of", "only replacement items may identify a replaced item")
        activation_reason = item.get("activation_reason")
        if activation_reason is not None and (not isinstance(activation_reason, str) or not activation_reason.strip()):
            diag(diagnostics, record, "error", "campaign.activation_reason", f"{base}.activation_reason", "nonempty string or null required")
        if cohort_role == "replacement":
            replacement_targets.append((base, item_id, replacement_of))
            if not isinstance(activation_reason, str) or not activation_reason.strip():
                diag(diagnostics, record, "error", "campaign.replacement_reason", f"{base}.activation_reason", "replacement activation requires a recorded reason")
        opportunity_id = require_typed_uuid(item, "opportunity_id", "opportunity", record, diagnostics, base)
        if opportunity_id is not None:
            opportunity_ids.append(opportunity_id)
        require_typed_uuid(item, "opportunity_revision_id", "opportunity-revision", record, diagnostics, base)
        require_string(item, "canonical_url", record, diagnostics, base)
        require_string(item, "organization", record, diagnostics, base)
        require_string(item, "title", record, diagnostics, base)
        require_typed_uuid(item, "freshness_evidence_id", "evidence", record, diagnostics, base)
        require_enum(item, "eligibility", {"eligible", "ineligible", "hold"}, record, diagnostics, base)
        require_enum(item, "fit_decision", {"pursue", "hold", "skip"}, record, diagnostics, base)
        priority = item.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
            diag(diagnostics, record, "error", "campaign.priority", f"{base}.priority", "integer from 1 through 5 required")
        require_id_list(item, "dependency_action_ids", "action", record, diagnostics, base=base)
        require_id_list(item, "artifact_revision_ids", "artifact-revision", record, diagnostics, base=base)
        plan_id = item.get("plan_id")
        revision = item.get("plan_revision_id")
        approval_hash = item.get("approval_hash")
        for key, candidate, prefix in (("plan_id", plan_id, "plan"), ("plan_revision_id", revision, "plan-revision")):
            if candidate is not None and not typed_uuid(candidate, prefix):
                diag(diagnostics, record, "error", "field.typed_uuid_required", f"{base}.{key}", f"null or canonical {prefix}-<uuid> required")
        if approval_hash is not None and (not isinstance(approval_hash, str) or not SHA256_RE.fullmatch(approval_hash)):
            diag(diagnostics, record, "error", "campaign.approval_hash", f"{base}.approval_hash", "null or lowercase SHA-256 required")
        state = require_enum(
            item,
            "state",
            {"queued", "ready", "approved", "succeeded", "failed", "ambiguous", "denied", "cancelled", "skipped", "blocked"},
            record,
            diagnostics,
            base,
        )
        if state is not None:
            observed[state] += 1
        attempted_at = optional_time(item, "attempted_at", record, diagnostics, base)
        effect_event = item.get("effect_event_id")
        if effect_event is not None and not typed_uuid(effect_event, "event"):
            diag(diagnostics, record, "error", "field.typed_uuid_required", f"{base}.effect_event_id", "null or canonical event-<uuid> required")
        if state in attempted_states and (attempted_at is None or effect_event is None):
            diag(diagnostics, record, "error", "campaign.attempt_receipt", base, "attempted work requires attempted_at and an exact effect event")
        if state not in attempted_states and effect_event is not None:
            diag(diagnostics, record, "error", "campaign.unexpected_effect_event", f"{base}.effect_event_id", "only attempted work may reference an effect event")
        if state in {"ready", "approved"} | attempted_states and (plan_id is None or revision is None or approval_hash is None):
            diag(diagnostics, record, "error", "campaign.effect_binding", base, "ready or attempted work must bind an exact effect plan revision and hash")
        failure_reason = item.get("failure_reason")
        if state in {"failed", "ambiguous", "denied", "cancelled", "skipped", "blocked"}:
            if not isinstance(failure_reason, str) or not failure_reason.strip():
                diag(diagnostics, record, "error", "campaign.failure_reason", f"{base}.failure_reason", "this disposition requires a nonempty reason")
        elif failure_reason is not None:
            diag(diagnostics, record, "error", "campaign.unexpected_failure_reason", f"{base}.failure_reason", "reason is only valid for non-success dispositions")
    if len(item_ids) != len(set(item_ids)):
        diag(diagnostics, record, "error", "campaign.duplicate_item", "$.items", "each campaign item_id must be unique")
    if len(slot_ids) != len(set(slot_ids)):
        diag(diagnostics, record, "error", "campaign.duplicate_slot", "$.items", "each campaign slot_id must be unique")
    known_item_ids = set(item_ids)
    for base, item_id, replacement_of in replacement_targets:
        if replacement_of not in known_item_ids:
            diag(diagnostics, record, "error", "campaign.missing_replacement_target", f"{base}.replacement_of", "replacement target must be another item in this campaign revision")
        elif replacement_of == item_id:
            diag(diagnostics, record, "error", "campaign.self_replacement", f"{base}.replacement_of", "an item cannot replace itself")
    if len(opportunity_ids) != len(set(opportunity_ids)):
        diag(diagnostics, record, "error", "campaign.duplicate_opportunity", "$.items", "each opportunity may appear once")
    if isinstance(roster_count, int) and not isinstance(roster_count, bool) and roster_count != primary_count:
        diag(diagnostics, record, "error", "campaign.roster_count_mismatch", "$.roster_count", "roster_count must equal the primary roster count")
    if isinstance(reserve_count, int) and not isinstance(reserve_count, bool) and reserve_count != observed_reserves:
        diag(diagnostics, record, "error", "campaign.reserve_count_mismatch", "$.reserve_count", "reserve_count must equal the reserve item count")
    if (
        isinstance(target_count, int)
        and not isinstance(target_count, bool)
        and isinstance(roster_count, int)
        and not isinstance(roster_count, bool)
        and target_count > roster_count
    ):
        diag(diagnostics, record, "error", "campaign.target_exceeds_roster", "$.target_count", "target quota cannot exceed roster_count")
    counts = value.get("counts")
    if not isinstance(counts, dict):
        diag(diagnostics, record, "error", "campaign.counts", "$.counts", "object required")
        counts = {}
    count_keys = {"queued", "ready", "approved", "attempted", "succeeded", "failed", "ambiguous", "denied", "cancelled", "skipped", "blocked"}
    reject_unknown(counts, count_keys, record, diagnostics, "$.counts")
    for key in sorted(count_keys):
        count = counts.get(key)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            diag(diagnostics, record, "error", "campaign.count", f"$.counts.{key}", "nonnegative integer required")
        else:
            expected = sum(observed[state] for state in attempted_states) if key == "attempted" else observed[key]
            if count != expected:
                diag(diagnostics, record, "error", "campaign.count_mismatch", f"$.counts.{key}", f"expected {expected}")
    attempted_count = sum(observed[state] for state in attempted_states)
    if isinstance(maximum_attempts, int) and not isinstance(maximum_attempts, bool) and attempted_count > maximum_attempts:
        diag(diagnostics, record, "error", "campaign.attempt_limit_exceeded", "$.maximum_attempts", f"observed {attempted_count} attempted effects")
    if value.get("state") == "completed" and isinstance(target_count, int) and observed["succeeded"] < target_count:
        diag(diagnostics, record, "error", "campaign.quota_not_met", "$.state", "completed campaign must meet its provider-acknowledged success quota")


def validate_action(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema", "action_id", "revision_id", "supersedes_revision_id", "recorded_at",
            "due_at", "opportunity_id", "kind", "state", "priority", "basis",
            "evidence_ids", "depends_on_action_ids", "resolution",
        },
        record,
        diagnostics,
    )
    action_id = require_typed_uuid(value, "action_id", "action", record, diagnostics)
    revision_id = require_typed_uuid(value, "revision_id", "action-revision", record, diagnostics)
    supersedes = value.get("supersedes_revision_id")
    if supersedes is not None and not typed_uuid(supersedes, "action-revision"):
        diag(diagnostics, record, "error", "field.typed_uuid_required", "$.supersedes_revision_id", "null or canonical action-revision-<uuid> required")
    if revision_id is not None and revision_id == supersedes:
        diag(diagnostics, record, "error", "revision.self_reference", "$.supersedes_revision_id", "revision cannot supersede itself")
    recorded = require_time(value, "recorded_at", record, diagnostics)
    due = optional_time(value, "due_at", record, diagnostics)
    if due is not None and recorded is not None and due < recorded:
        diag(diagnostics, record, "warning", "action.created_overdue", "$.due_at", "action was already overdue when recorded")
    opportunity_id = value.get("opportunity_id")
    if opportunity_id is not None and not typed_uuid(opportunity_id, "opportunity"):
        diag(diagnostics, record, "error", "field.typed_uuid_required", "$.opportunity_id", "null or canonical opportunity-<uuid> required")
    require_enum(
        value,
        "kind",
        {"research", "clarify", "prepare", "apply", "follow_up", "respond", "schedule", "reconcile", "review", "other"},
        record,
        diagnostics,
    )
    state = require_enum(value, "state", {"pending", "blocked", "done", "cancelled"}, record, diagnostics)
    require_enum(value, "priority", {"low", "normal", "high", "urgent"}, record, diagnostics)
    require_string(value, "basis", record, diagnostics)
    require_id_list(value, "evidence_ids", "evidence", record, diagnostics)
    dependencies = require_id_list(value, "depends_on_action_ids", "action", record, diagnostics)
    if action_id is not None and action_id in dependencies:
        diag(diagnostics, record, "error", "action.self_dependency", "$.depends_on_action_ids", "action cannot depend on itself")
    resolution = value.get("resolution")
    if state in {"done", "cancelled"}:
        if not isinstance(resolution, str) or not resolution.strip():
            diag(diagnostics, record, "error", "action.resolution_required", "$.resolution", "done or cancelled action requires a resolution")
    elif resolution is not None:
        diag(diagnostics, record, "error", "action.premature_resolution", "$.resolution", "only done or cancelled actions may carry a resolution")


def validate_evidence(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema",
            "id",
            "recorded_at",
            "source",
            "integrity",
            "selector",
            "excerpt",
            "summary",
            "redactions",
        },
        record,
        diagnostics,
    )
    require_typed_uuid(value, "id", "evidence", record, diagnostics)
    recorded = require_time(value, "recorded_at", record, diagnostics)
    source = value.get("source")
    if not isinstance(source, dict):
        diag(diagnostics, record, "error", "evidence.source", "$.source", "object required")
        source = {}
    reject_unknown(
        source,
        {"kind", "locator", "captured_at", "provider_id", "external_id", "actor"},
        record,
        diagnostics,
        "$.source",
    )
    kind = require_enum(
        source,
        "kind",
        {"file", "url", "user_statement", "email", "calendar", "provider_record", "manual"},
        record,
        diagnostics,
        "$.source",
    )
    locator = require_string(source, "locator", record, diagnostics, "$.source")
    captured = require_time(source, "captured_at", record, diagnostics, "$.source")
    if recorded is not None and captured is not None and captured > recorded:
        diag(
            diagnostics,
            record,
            "error",
            "evidence.future_capture",
            "$.source.captured_at",
            "capture time cannot follow receipt time",
        )
    if kind == "file" and locator is not None:
        validate_relative_locator(locator, record, diagnostics, "$.source.locator")
    provider_id = source.get("provider_id")
    if provider_id is not None and (
        not isinstance(provider_id, str) or not PROVIDER_ID_RE.fullmatch(provider_id)
    ):
        diag(
            diagnostics,
            record,
            "error",
            "provider.id",
            "$.source.provider_id",
            "lowercase kebab-case provider identifier required",
        )
    if kind == "user_statement" and not isinstance(source.get("actor"), str):
        diag(
            diagnostics,
            record,
            "error",
            "evidence.attestor_required",
            "$.source.actor",
            "user statements require a named attesting actor role",
        )

    integrity = value.get("integrity")
    if not isinstance(integrity, dict):
        diag(
            diagnostics,
            record,
            "error",
            "evidence.integrity",
            "$.integrity",
            "object required",
        )
        integrity = {}
    reject_unknown(
        integrity,
        {"sha256", "byte_length", "media_type"},
        record,
        diagnostics,
        "$.integrity",
    )
    sha = integrity.get("sha256")
    if sha is not None and (not isinstance(sha, str) or not SHA256_RE.fullmatch(sha)):
        diag(
            diagnostics,
            record,
            "error",
            "evidence.sha256",
            "$.integrity.sha256",
            "lowercase SHA-256 required",
        )
    if kind in {"file", "provider_record"} and sha is None:
        diag(
            diagnostics,
            record,
            "error",
            "evidence.sha256_required",
            "$.integrity.sha256",
            "byte-addressable captures require SHA-256",
        )
    byte_length = integrity.get("byte_length")
    if byte_length is not None and (
        isinstance(byte_length, bool) or not isinstance(byte_length, int) or byte_length < 0
    ):
        diag(
            diagnostics,
            record,
            "error",
            "evidence.byte_length",
            "$.integrity.byte_length",
            "nonnegative integer required",
        )
    for key, limit in (("excerpt", 1000), ("summary", 4000)):
        item = value.get(key)
        if item is not None and (not isinstance(item, str) or len(item) > limit):
            diag(
                diagnostics,
                record,
                "error",
                "evidence.bounded_text",
                f"$.{key}",
                f"string of at most {limit} characters required",
            )
    redactions = value.get("redactions")
    if not isinstance(redactions, list) or not all(isinstance(item, str) for item in redactions):
        diag(
            diagnostics,
            record,
            "error",
            "evidence.redactions",
            "$.redactions",
            "string array required",
        )


def validate_fact(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema",
            "fact_id",
            "revision_id",
            "supersedes_revision_id",
            "recorded_at",
            "subject_id",
            "predicate",
            "scope",
            "operation",
            "value",
            "confidence",
            "confidence_basis",
            "evidence_ids",
            "contradicts_fact_ids",
        },
        record,
        diagnostics,
    )
    fact_id = require_typed_uuid(value, "fact_id", "fact", record, diagnostics)
    revision_id = require_typed_uuid(value, "revision_id", "fact-revision", record, diagnostics)
    supersedes = value.get("supersedes_revision_id")
    if supersedes is not None and not typed_uuid(supersedes, "fact-revision"):
        diag(
            diagnostics,
            record,
            "error",
            "field.typed_uuid_required",
            "$.supersedes_revision_id",
            "null or canonical fact-revision-<uuid> required",
        )
    if revision_id is not None and supersedes == revision_id:
        diag(
            diagnostics,
            record,
            "error",
            "revision.self_reference",
            "$.supersedes_revision_id",
            "revision cannot supersede itself",
        )
    require_time(value, "recorded_at", record, diagnostics)
    require_typed_uuid(value, "subject_id", "subject", record, diagnostics)
    predicate = require_string(value, "predicate", record, diagnostics)
    if predicate is not None and not PREDICATE_RE.fullmatch(predicate):
        diag(
            diagnostics,
            record,
            "error",
            "fact.predicate",
            "$.predicate",
            "lowercase dotted token required",
        )
    scope = value.get("scope", {})
    if not isinstance(scope, dict):
        diag(diagnostics, record, "error", "fact.scope", "$.scope", "object required")
    operation = require_enum(
        value, "operation", {"assert", "retract"}, record, diagnostics
    )
    if operation == "assert" and "value" not in value:
        diag(
            diagnostics,
            record,
            "error",
            "fact.value_required",
            "$.value",
            "assert revisions require a value",
        )
    if operation == "retract" and "value" in value:
        diag(
            diagnostics,
            record,
            "error",
            "fact.retract_has_value",
            "$.value",
            "retract revisions must not contain a value",
        )
    require_enum(value, "confidence", {"low", "medium", "high"}, record, diagnostics)
    require_string(value, "confidence_basis", record, diagnostics)
    require_id_list(
        value, "evidence_ids", "evidence", record, diagnostics, nonempty=True
    )
    contradicts = require_id_list(
        value, "contradicts_fact_ids", "fact", record, diagnostics
    )
    if fact_id is not None and fact_id in contradicts:
        diag(
            diagnostics,
            record,
            "error",
            "fact.self_contradiction",
            "$.contradicts_fact_ids",
            "fact cannot contradict itself",
        )


def validate_compensation(
    value: Any, record: LoadedRecord, diagnostics: list[Diagnostic]
) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        diag(
            diagnostics,
            record,
            "error",
            "opportunity.compensation",
            "$.normalized.compensation",
            "object or null required",
        )
        return
    reject_unknown(
        value,
        {"raw", "currency", "minimum", "maximum", "period"},
        record,
        diagnostics,
        "$.normalized.compensation",
    )
    require_string(value, "raw", record, diagnostics, "$.normalized.compensation")
    currency = value.get("currency")
    if not isinstance(currency, str) or not CURRENCY_RE.fullmatch(currency):
        diag(
            diagnostics,
            record,
            "error",
            "opportunity.currency",
            "$.normalized.compensation.currency",
            "ISO 4217 three-letter currency code required",
        )
    require_enum(
        value,
        "period",
        {"hour", "day", "week", "month", "year", "project", "unknown"},
        record,
        diagnostics,
        "$.normalized.compensation",
    )
    parsed: dict[str, Decimal] = {}
    for key in ("minimum", "maximum"):
        item = value.get(key)
        if item is None:
            continue
        if not isinstance(item, str):
            diag(
                diagnostics,
                record,
                "error",
                "opportunity.decimal_string",
                f"$.normalized.compensation.{key}",
                "decimal values must be strings",
            )
            continue
        try:
            decimal = Decimal(item)
            if not decimal.is_finite():
                raise InvalidOperation
            parsed[key] = decimal
        except InvalidOperation:
            diag(
                diagnostics,
                record,
                "error",
                "opportunity.decimal_string",
                f"$.normalized.compensation.{key}",
                "finite decimal string required",
            )
    if "minimum" in parsed and "maximum" in parsed and parsed["minimum"] > parsed["maximum"]:
        diag(
            diagnostics,
            record,
            "error",
            "opportunity.compensation_range",
            "$.normalized.compensation",
            "minimum cannot exceed maximum",
        )


def validate_opportunity(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema",
            "opportunity_id",
            "revision_id",
            "supersedes_revision_id",
            "recorded_at",
            "title",
            "organization",
            "origins",
            "evidence_ids",
            "normalized",
            "application",
            "normalization_warnings",
        },
        record,
        diagnostics,
    )
    require_typed_uuid(value, "opportunity_id", "opportunity", record, diagnostics)
    revision_id = require_typed_uuid(
        value, "revision_id", "opportunity-revision", record, diagnostics
    )
    supersedes = value.get("supersedes_revision_id")
    if supersedes is not None and not typed_uuid(supersedes, "opportunity-revision"):
        diag(
            diagnostics,
            record,
            "error",
            "field.typed_uuid_required",
            "$.supersedes_revision_id",
            "null or canonical opportunity-revision-<uuid> required",
        )
    if revision_id is not None and supersedes == revision_id:
        diag(
            diagnostics,
            record,
            "error",
            "revision.self_reference",
            "$.supersedes_revision_id",
            "revision cannot supersede itself",
        )
    require_time(value, "recorded_at", record, diagnostics)
    require_string(value, "title", record, diagnostics)
    organization = value.get("organization")
    if not isinstance(organization, dict):
        diag(
            diagnostics,
            record,
            "error",
            "opportunity.organization",
            "$.organization",
            "object required",
        )
    else:
        reject_unknown(organization, {"name", "id"}, record, diagnostics, "$.organization")
        require_string(organization, "name", record, diagnostics, "$.organization")
    require_id_list(
        value, "evidence_ids", "evidence", record, diagnostics, nonempty=True
    )
    origins = value.get("origins")
    if not isinstance(origins, list) or not origins:
        diag(
            diagnostics,
            record,
            "error",
            "opportunity.origins",
            "$.origins",
            "nonempty origin array required",
        )
        origins = []
    for index, origin in enumerate(origins):
        base = f"$.origins[{index}]"
        if not isinstance(origin, dict):
            diag(diagnostics, record, "error", "opportunity.origin", base, "object required")
            continue
        reject_unknown(
            origin,
            {"provider_id", "external_id", "url", "retrieved_at", "evidence_id", "adapter_version"},
            record,
            diagnostics,
            base,
        )
        provider_id = require_string(origin, "provider_id", record, diagnostics, base)
        if provider_id is not None and not PROVIDER_ID_RE.fullmatch(provider_id):
            diag(
                diagnostics,
                record,
                "error",
                "provider.id",
                f"{base}.provider_id",
                "lowercase kebab-case provider identifier required",
            )
        require_time(origin, "retrieved_at", record, diagnostics, base)
        evidence_id = origin.get("evidence_id")
        if not typed_uuid(evidence_id, "evidence"):
            diag(
                diagnostics,
                record,
                "error",
                "field.typed_uuid_required",
                f"{base}.evidence_id",
                "canonical evidence-<uuid> identifier required",
            )
        if not origin.get("external_id") and not origin.get("url"):
            diag(
                diagnostics,
                record,
                "warning",
                "opportunity.weak_origin",
                base,
                "origin has neither external identifier nor URL",
            )
    normalized = value.get("normalized")
    unknown_values: list[str] = []
    if not isinstance(normalized, dict):
        diag(
            diagnostics,
            record,
            "error",
            "opportunity.normalized",
            "$.normalized",
            "object required",
        )
        normalized = {}
    reject_unknown(
        normalized,
        {
            "employment_type",
            "workplace",
            "seniority",
            "work_locations",
            "eligible_applicant_locations",
            "authorization_text",
            "schedule",
            "compensation",
        },
        record,
        diagnostics,
        "$.normalized",
    )
    enums = {
        "employment_type": {"full_time", "part_time", "contract", "temporary", "internship", "freelance", "unknown", "other"},
        "workplace": {"onsite", "hybrid", "remote", "unknown", "other"},
        "seniority": {"entry", "junior", "mid", "senior", "staff", "principal", "lead", "manager", "director", "executive", "unknown", "other"},
    }
    for key, allowed in enums.items():
        enum_value = require_enum(normalized, key, allowed, record, diagnostics, "$.normalized")
        if enum_value in {"unknown", "other"}:
            unknown_values.append(key)
    require_string_list(normalized, "work_locations", record, diagnostics, nonempty=True, base="$.normalized")
    require_string_list(
        normalized,
        "eligible_applicant_locations",
        record,
        diagnostics,
        nonempty=True,
        base="$.normalized",
    )
    require_string(normalized, "authorization_text", record, diagnostics, "$.normalized")
    schedule = normalized.get("schedule")
    if not isinstance(schedule, dict):
        diag(diagnostics, record, "error", "opportunity.schedule", "$.normalized.schedule", "object required")
        schedule = {}
    reject_unknown(
        schedule,
        {"timezone_requirements", "working_hours", "travel", "on_call"},
        record,
        diagnostics,
        "$.normalized.schedule",
    )
    require_string_list(schedule, "timezone_requirements", record, diagnostics, base="$.normalized.schedule")
    for key in ("working_hours", "travel", "on_call"):
        item = schedule.get(key)
        if item is not None and (not isinstance(item, str) or not item.strip()):
            diag(diagnostics, record, "error", "opportunity.schedule_text", f"$.normalized.schedule.{key}", "string or null required")
    validate_compensation(normalized.get("compensation"), record, diagnostics)
    application = value.get("application")
    if not isinstance(application, dict):
        diag(diagnostics, record, "error", "opportunity.application", "$.application", "object required")
        application = {}
    reject_unknown(
        application,
        {"canonical_url", "published_at", "modified_at", "expires_at", "last_verified_at", "source_description_sha256"},
        record,
        diagnostics,
        "$.application",
    )
    canonical_application_url = require_string(application, "canonical_url", record, diagnostics, "$.application")
    if canonical_application_url is not None:
        parts = urlsplit(canonical_application_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            diag(diagnostics, record, "error", "opportunity.application_url", "$.application.canonical_url", "absolute HTTP(S) URL required")
    published = optional_time(application, "published_at", record, diagnostics, "$.application")
    modified = optional_time(application, "modified_at", record, diagnostics, "$.application")
    expires_at = optional_time(application, "expires_at", record, diagnostics, "$.application")
    verified = require_time(application, "last_verified_at", record, diagnostics, "$.application")
    if published is not None and modified is not None and modified < published:
        diag(diagnostics, record, "error", "opportunity.modified_before_published", "$.application.modified_at", "modified_at cannot precede published_at")
    if published is not None and expires_at is not None and expires_at <= published:
        diag(diagnostics, record, "error", "opportunity.expiry_order", "$.application.expires_at", "expires_at must follow published_at")
    recorded_at = parse_time(value.get("recorded_at"))
    if verified is not None and recorded_at is not None and verified > recorded_at:
        diag(diagnostics, record, "error", "opportunity.future_verification", "$.application.last_verified_at", "verification cannot follow the opportunity revision")
    description_hash = application.get("source_description_sha256")
    if not isinstance(description_hash, str) or not SHA256_RE.fullmatch(description_hash):
        diag(diagnostics, record, "error", "opportunity.description_hash", "$.application.source_description_sha256", "lowercase SHA-256 required")
    warnings = value.get("normalization_warnings")
    if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
        diag(
            diagnostics,
            record,
            "error",
            "opportunity.normalization_warnings",
            "$.normalization_warnings",
            "string array required",
        )
        warnings = []
    if unknown_values and not warnings:
        diag(
            diagnostics,
            record,
            "warning",
            "opportunity.unexplained_unknown",
            "$.normalization_warnings",
            "unknown or other normalized fields should preserve a mapping warning",
        )


def validate_event(record: LoadedRecord, diagnostics: list[Diagnostic]) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema",
            "id",
            "opportunity_id",
            "previous_event_id",
            "recorded_at",
            "effective_at",
            "actor",
            "type",
            "evidence_ids",
            "status_before",
            "status_after",
            "outcome",
            "correction_of_event_id",
            "provider_status",
            "note",
            "effect_result",
            "effect_reconciliation",
            "interaction",
        },
        record,
        diagnostics,
    )
    event_id = require_typed_uuid(value, "id", "event", record, diagnostics)
    require_typed_uuid(value, "opportunity_id", "opportunity", record, diagnostics)
    previous = value.get("previous_event_id")
    if previous is not None and not typed_uuid(previous, "event"):
        diag(
            diagnostics,
            record,
            "error",
            "field.typed_uuid_required",
            "$.previous_event_id",
            "null or canonical event-<uuid> required",
        )
    if event_id is not None and previous == event_id:
        diag(
            diagnostics,
            record,
            "error",
            "event.self_reference",
            "$.previous_event_id",
            "event cannot follow itself",
        )
    require_time(value, "recorded_at", record, diagnostics)
    require_time(value, "effective_at", record, diagnostics)
    actor = value.get("actor")
    if not isinstance(actor, dict):
        diag(diagnostics, record, "error", "event.actor", "$.actor", "object required")
    else:
        reject_unknown(actor, {"kind", "id"}, record, diagnostics, "$.actor")
        require_enum(
            actor,
            "kind",
            {"user", "agent", "provider", "employer", "recruiter", "other"},
            record,
            diagnostics,
            "$.actor",
        )
    event_type = require_enum(value, "type", EVENT_TYPES, record, diagnostics)
    evidence_ids = require_id_list(value, "evidence_ids", "evidence", record, diagnostics)
    if event_type == "application_submitted" and not evidence_ids:
        diag(
            diagnostics,
            record,
            "error",
            "event.application_evidence_required",
            "$.evidence_ids",
            "application_submitted requires at least one evidence receipt",
        )
    before = value.get("status_before")
    if before is not None and before not in STAGES:
        diag(
            diagnostics,
            record,
            "error",
            "event.status_before",
            "$.status_before",
            "null or a defined pipeline stage required",
        )
    after = require_enum(value, "status_after", set(STAGES), record, diagnostics)
    interaction = value.get("interaction")
    if interaction is not None:
        if not isinstance(interaction, dict):
            diag(diagnostics, record, "error", "event.interaction", "$.interaction", "object required")
        else:
            reject_unknown(interaction, {"kind", "schedule_state", "calendar_state"}, record, diagnostics, "$.interaction")
            interaction_kind = require_enum(
                interaction,
                "kind",
                {"recruiter_chat", "screen", "interview", "assessment", "offer_discussion", "other"},
                record,
                diagnostics,
                "$.interaction",
            )
            require_enum(
                interaction,
                "schedule_state",
                {"none", "proposed", "scheduled", "completed", "cancelled"},
                record,
                diagnostics,
                "$.interaction",
            )
            require_enum(
                interaction,
                "calendar_state",
                {"none", "tentative", "confirmed", "cancelled", "unknown"},
                record,
                diagnostics,
                "$.interaction",
            )
            if interaction_kind != "interview" and after == "interviewing":
                diag(diagnostics, record, "error", "event.non_interview_stage", "$.interaction.kind", "a scheduled non-interview interaction must not enter interviewing")
    outcome = value.get("outcome")
    if after == "closed":
        if not isinstance(outcome, dict):
            diag(
                diagnostics,
                record,
                "error",
                "event.closed_without_outcome",
                "$.outcome",
                "closed status requires a terminal outcome",
            )
        else:
            reject_unknown(outcome, {"kind", "reason"}, record, diagnostics, "$.outcome")
            require_enum(outcome, "kind", OUTCOMES, record, diagnostics, "$.outcome")
    elif outcome is not None:
        diag(
            diagnostics,
            record,
            "error",
            "event.open_with_outcome",
            "$.outcome",
            "terminal outcome is allowed only with closed status",
        )
    correction = value.get("correction_of_event_id")
    if correction is not None and not typed_uuid(correction, "event"):
        diag(
            diagnostics,
            record,
            "error",
            "field.typed_uuid_required",
            "$.correction_of_event_id",
            "null or canonical event-<uuid> required",
        )
    if event_type in {"correction", "reopened"} and correction is None:
        diag(
            diagnostics,
            record,
            "error",
            "event.correction_target_required",
            "$.correction_of_event_id",
            "correction and reopen events require a target event",
        )
    if event_type in {"correction", "reopened"} and not evidence_ids:
        diag(
            diagnostics,
            record,
            "error",
            "event.correction_evidence_required",
            "$.evidence_ids",
            "correction and reopen events require evidence",
        )
    if after == "interviewing" and event_type not in {
        "interview_scheduled",
        "interview_completed",
        "correction",
        "reopened",
    }:
        diag(
            diagnostics,
            record,
            "error",
            "event.proposal_is_not_scheduled",
            "$.status_after",
            "only scheduled/completed interviews or evidenced corrections may enter interviewing",
        )
    required_stage = {
        "application_submitted": "applied",
        "interview_scheduled": "interviewing",
        "offer_received": "offer",
        "outcome_recorded": "closed",
    }.get(event_type)
    if required_stage is not None and after != required_stage:
        diag(
            diagnostics,
            record,
            "error",
            "event.type_stage_mismatch",
            "$.status_after",
            f"{event_type} requires status_after={required_stage}",
        )
    provider_status = value.get("provider_status")
    if provider_status is not None:
        if not isinstance(provider_status, dict):
            diag(
                diagnostics,
                record,
                "error",
                "event.provider_status",
                "$.provider_status",
                "object required",
            )
        else:
            reject_unknown(
                provider_status,
                {"provider_id", "raw", "mapped_status", "mapping_version"},
                record,
                diagnostics,
                "$.provider_status",
            )
            provider_id = require_string(provider_status, "provider_id", record, diagnostics, "$.provider_status")
            if provider_id is not None and not PROVIDER_ID_RE.fullmatch(provider_id):
                diag(diagnostics, record, "error", "provider.id", "$.provider_status.provider_id", "lowercase kebab-case provider identifier required")
            require_string(provider_status, "raw", record, diagnostics, "$.provider_status")
            require_string(provider_status, "mapping_version", record, diagnostics, "$.provider_status")
            mapped = require_enum(
                provider_status,
                "mapped_status",
                set(STAGES) | {"unknown"},
                record,
                diagnostics,
                "$.provider_status",
            )
            if mapped == "unknown":
                diag(diagnostics, record, "warning", "event.provider_status_unmapped", "$.provider_status.mapped_status", "provider status remains unmapped")
            elif mapped is not None and after is not None and mapped != after:
                diag(diagnostics, record, "error", "event.provider_status_mismatch", "$.provider_status.mapped_status", "mapped provider status must equal status_after")
    effect_result = value.get("effect_result")
    if event_type == "effect_executed" and effect_result is None:
        diag(diagnostics, record, "error", "event.effect_result_required", "$.effect_result", "effect_executed requires an execution result")
    if event_type != "effect_executed" and effect_result is not None:
        diag(diagnostics, record, "error", "event.effect_result_misattached", "$.effect_result", "effect_result is valid only on effect_executed")
    if effect_result is not None:
        if not isinstance(effect_result, dict):
            diag(
                diagnostics,
                record,
                "error",
                "event.effect_result",
                "$.effect_result",
                "object required",
            )
        else:
            reject_unknown(
                effect_result,
                {"plan_id", "plan_revision_id", "approval_hash", "outcome", "provider_receipt"},
                record,
                diagnostics,
                "$.effect_result",
            )
            require_typed_uuid(effect_result, "plan_id", "plan", record, diagnostics, "$.effect_result")
            require_typed_uuid(
                effect_result, "plan_revision_id", "plan-revision", record, diagnostics, "$.effect_result"
            )
            approval_hash = effect_result.get("approval_hash")
            if not isinstance(approval_hash, str) or not SHA256_RE.fullmatch(approval_hash):
                diag(
                    diagnostics,
                    record,
                    "error",
                    "event.approval_hash",
                    "$.effect_result.approval_hash",
                    "lowercase SHA-256 required",
                )
            effect_outcome = require_enum(
                effect_result,
                "outcome",
                {"succeeded", "failed", "ambiguous", "denied", "cancelled"},
                record,
                diagnostics,
                "$.effect_result",
            )
            provider_receipt = effect_result.get("provider_receipt")
            if effect_outcome == "succeeded" and provider_receipt is None:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "event.succeeded_receipt_required",
                    "$.effect_result.provider_receipt",
                    "a succeeded effect requires a provider receipt evidence identifier",
                )
            elif provider_receipt is not None and not typed_uuid(provider_receipt, "evidence"):
                diag(diagnostics, record, "error", "field.typed_uuid_required", "$.effect_result.provider_receipt", "null or canonical evidence-<uuid> required")
    reconciliation = value.get("effect_reconciliation")
    if event_type == "effect_reconciled" and reconciliation is None:
        diag(diagnostics, record, "error", "event.effect_reconciliation_required", "$.effect_reconciliation", "effect_reconciled requires reconciliation details")
    if event_type != "effect_reconciled" and reconciliation is not None:
        diag(diagnostics, record, "error", "event.effect_reconciliation_misattached", "$.effect_reconciliation", "effect_reconciliation is valid only on effect_reconciled")
    if reconciliation is not None:
        if not isinstance(reconciliation, dict):
            diag(diagnostics, record, "error", "event.effect_reconciliation", "$.effect_reconciliation", "object required")
        else:
            reject_unknown(
                reconciliation,
                {"plan_id", "plan_revision_id", "approval_hash", "ambiguous_event_id", "resolution"},
                record,
                diagnostics,
                "$.effect_reconciliation",
            )
            require_typed_uuid(reconciliation, "plan_id", "plan", record, diagnostics, "$.effect_reconciliation")
            require_typed_uuid(reconciliation, "plan_revision_id", "plan-revision", record, diagnostics, "$.effect_reconciliation")
            require_typed_uuid(reconciliation, "ambiguous_event_id", "event", record, diagnostics, "$.effect_reconciliation")
            approval_hash = reconciliation.get("approval_hash")
            if not isinstance(approval_hash, str) or not SHA256_RE.fullmatch(approval_hash):
                diag(diagnostics, record, "error", "event.approval_hash", "$.effect_reconciliation.approval_hash", "lowercase SHA-256 required")
            require_enum(reconciliation, "resolution", {"occurred", "not_occurred"}, record, diagnostics, "$.effect_reconciliation")
            if before != after:
                diag(diagnostics, record, "error", "event.reconciliation_status_change", "$.status_after", "effect reconciliation must not change pipeline status")
            if not evidence_ids:
                diag(diagnostics, record, "error", "event.reconciliation_evidence_required", "$.evidence_ids", "effect reconciliation requires evidence")


def approval_basis(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "career.effect_approval_basis.v1",
        "plan_id": plan.get("plan_id"),
        "opportunity_id": plan.get("opportunity_id"),
        "effect": plan.get("effect"),
        "expires_at": plan.get("expires_at"),
    }


def validate_plan(
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    as_of: datetime | None = None,
) -> None:
    value = record.value
    reject_unknown(
        value,
        {
            "schema",
            "plan_id",
            "revision_id",
            "supersedes_revision_id",
            "created_at",
            "recorded_at",
            "opportunity_id",
            "effect",
            "expires_at",
            "approval",
            "approval_hash",
            "display_preview",
        },
        record,
        diagnostics,
    )
    require_typed_uuid(value, "plan_id", "plan", record, diagnostics)
    revision_id = require_typed_uuid(value, "revision_id", "plan-revision", record, diagnostics)
    supersedes = value.get("supersedes_revision_id")
    if supersedes is not None and not typed_uuid(supersedes, "plan-revision"):
        diag(
            diagnostics,
            record,
            "error",
            "field.typed_uuid_required",
            "$.supersedes_revision_id",
            "null or canonical plan-revision-<uuid> required",
        )
    if revision_id is not None and supersedes == revision_id:
        diag(
            diagnostics,
            record,
            "error",
            "revision.self_reference",
            "$.supersedes_revision_id",
            "revision cannot supersede itself",
        )
    created = require_time(value, "created_at", record, diagnostics)
    recorded = require_time(value, "recorded_at", record, diagnostics)
    expires = require_time(value, "expires_at", record, diagnostics)
    if created is not None and recorded is not None and recorded < created:
        diag(diagnostics, record, "error", "plan.revision_before_creation", "$.recorded_at", "plan revision cannot precede plan creation")
    if created is not None and expires is not None and expires <= created:
        diag(diagnostics, record, "error", "plan.invalid_expiry", "$.expires_at", "expires_at must follow created_at")
    opportunity_id = value.get("opportunity_id")
    if opportunity_id is not None and not typed_uuid(opportunity_id, "opportunity"):
        diag(
            diagnostics,
            record,
            "error",
            "field.typed_uuid_required",
            "$.opportunity_id",
            "null or canonical opportunity-<uuid> required",
        )
    effect = value.get("effect")
    if not isinstance(effect, dict):
        diag(diagnostics, record, "error", "plan.effect", "$.effect", "object required")
        effect = {}
    reject_unknown(
        effect,
        {
            "action", "provider_id", "account_id", "target", "payload", "attachments",
            "idempotency_key", "effect_class", "data_disclosure", "expected_remote_state",
        },
        record,
        diagnostics,
        "$.effect",
    )
    require_string(effect, "action", record, diagnostics, "$.effect")
    provider_id = require_string(effect, "provider_id", record, diagnostics, "$.effect")
    if provider_id is not None and not PROVIDER_ID_RE.fullmatch(provider_id):
        diag(
            diagnostics,
            record,
            "error",
            "provider.id",
            "$.effect.provider_id",
            "lowercase kebab-case provider identifier required",
        )
    require_string(effect, "account_id", record, diagnostics, "$.effect")
    if "target" not in effect or effect.get("target") in (None, "", {}):
        diag(
            diagnostics,
            record,
            "error",
            "plan.target_required",
            "$.effect.target",
            "exact target required",
        )
    if "payload" not in effect:
        diag(
            diagnostics,
            record,
            "error",
            "plan.payload_required",
            "$.effect.payload",
            "exact payload required",
        )
    require_string(effect, "idempotency_key", record, diagnostics, "$.effect")
    require_enum(effect, "effect_class", EFFECT_CLASSES, record, diagnostics, "$.effect")
    disclosures = effect.get("data_disclosure")
    if not isinstance(disclosures, list):
        diag(diagnostics, record, "error", "plan.data_disclosure", "$.effect.data_disclosure", "array required, including an empty array when nothing is disclosed")
        disclosures = []
    for index, disclosure in enumerate(disclosures):
        base = f"$.effect.data_disclosure[{index}]"
        if not isinstance(disclosure, dict):
            diag(diagnostics, record, "error", "plan.disclosure_item", base, "object required")
            continue
        reject_unknown(disclosure, {"field", "purpose", "recipient", "sensitivity"}, record, diagnostics, base)
        for key in ("field", "purpose", "recipient"):
            require_string(disclosure, key, record, diagnostics, base)
        require_enum(disclosure, "sensitivity", {"public", "personal", "sensitive"}, record, diagnostics, base)
    expected_state = effect.get("expected_remote_state")
    if expected_state is not None:
        if not isinstance(expected_state, dict):
            diag(diagnostics, record, "error", "plan.expected_remote_state", "$.effect.expected_remote_state", "object or null required")
        else:
            reject_unknown(expected_state, {"version", "sha256", "selector"}, record, diagnostics, "$.effect.expected_remote_state")
            if not expected_state:
                diag(diagnostics, record, "error", "plan.expected_remote_state_empty", "$.effect.expected_remote_state", "expected state must contain a version, hash, or selector")
            for key in ("version", "selector"):
                item = expected_state.get(key)
                if item is not None and (not isinstance(item, str) or not item.strip()):
                    diag(diagnostics, record, "error", "plan.expected_remote_state_text", f"$.effect.expected_remote_state.{key}", "nonempty string or null required")
            state_hash = expected_state.get("sha256")
            if state_hash is not None and (not isinstance(state_hash, str) or not SHA256_RE.fullmatch(state_hash)):
                diag(diagnostics, record, "error", "plan.expected_remote_state_hash", "$.effect.expected_remote_state.sha256", "lowercase SHA-256 or null required")
    attachments = effect.get("attachments")
    if not isinstance(attachments, list):
        diag(
            diagnostics,
            record,
            "error",
            "plan.attachments",
            "$.effect.attachments",
            "attachment array required",
        )
        attachments = []
    for index, attachment in enumerate(attachments):
        base = f"$.effect.attachments[{index}]"
        if not isinstance(attachment, dict):
            diag(diagnostics, record, "error", "plan.attachment", base, "object required")
            continue
        reject_unknown(attachment, {"name", "sha256"}, record, diagnostics, base)
        require_string(attachment, "name", record, diagnostics, base)
        sha = attachment.get("sha256")
        if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
            diag(
                diagnostics,
                record,
                "error",
                "plan.attachment_hash",
                f"{base}.sha256",
                "lowercase SHA-256 required",
            )
    approval = value.get("approval")
    if not isinstance(approval, dict):
        diag(diagnostics, record, "error", "plan.approval", "$.approval", "object required")
        approval = {}
    reject_unknown(
        approval,
        {"state", "approved_by", "approved_at"},
        record,
        diagnostics,
        "$.approval",
    )
    approval_state = require_enum(
        approval,
        "state",
        {"pending", "approved", "denied", "revoked", "expired"},
        record,
        diagnostics,
        "$.approval",
    )
    if approval_state == "approved":
        require_string(approval, "approved_by", record, diagnostics, "$.approval")
        approved_at = require_time(approval, "approved_at", record, diagnostics, "$.approval")
        if created is not None and approved_at is not None and approved_at < created:
            diag(diagnostics, record, "error", "plan.approval_before_creation", "$.approval.approved_at", "approval cannot precede plan creation")
        if expires is not None and approved_at is not None and approved_at >= expires:
            diag(diagnostics, record, "error", "plan.approval_after_expiry", "$.approval.approved_at", "approval must precede expiry")
    elif approval.get("approved_by") is not None or approval.get("approved_at") is not None:
        diag(
            diagnostics,
            record,
            "error",
            "plan.approval_metadata",
            "$.approval",
            "approval actor and time are valid only for approved state",
        )
    try:
        expected_hash = canonical_sha256(approval_basis(value))
    except (TypeError, ValueError) as exc:
        diag(
            diagnostics,
            record,
            "error",
            "plan.hash_basis",
            "$",
            f"approval basis is not canonical JSON: {exc}",
        )
        expected_hash = None
    supplied_hash = value.get("approval_hash")
    if expected_hash is not None and supplied_hash != expected_hash:
        diag(
            diagnostics,
            record,
            "error",
            "plan.approval_hash_mismatch",
            "$.approval_hash",
            f"expected {expected_hash}",
        )
def validate_record_structure(
    record: LoadedRecord,
    diagnostics: list[Diagnostic],
    as_of: datetime | None = None,
) -> None:
    walk_numbers(record.value, record, diagnostics)
    schema = record.value.get("schema")
    if schema not in CORE_SCHEMAS:
        diag(
            diagnostics,
            record,
            "error",
            "record.unknown_schema",
            "$.schema",
            "expected one of: " + ", ".join(sorted(CORE_SCHEMAS)),
        )
        return
    if schema == EVIDENCE_SCHEMA:
        validate_evidence(record, diagnostics)
    elif schema == FACT_SCHEMA:
        validate_fact(record, diagnostics)
    elif schema == OPPORTUNITY_SCHEMA:
        validate_opportunity(record, diagnostics)
    elif schema == EVENT_SCHEMA:
        validate_event(record, diagnostics)
    elif schema == PLAN_SCHEMA:
        validate_plan(record, diagnostics, as_of)
    elif schema == PROFILE_SCHEMA:
        validate_profile(record, diagnostics)
    elif schema == SEARCH_POLICY_SCHEMA:
        validate_search_policy(record, diagnostics)
    elif schema == ARTIFACT_SCHEMA:
        validate_artifact(record, diagnostics)
    elif schema == CAMPAIGN_SCHEMA:
        validate_campaign(record, diagnostics)
    elif schema == ACTION_SCHEMA:
        validate_action(record, diagnostics)


def record_primary_id(record: LoadedRecord) -> tuple[str, str] | None:
    schema = record.value.get("schema")
    key = {
        EVIDENCE_SCHEMA: "id",
        FACT_SCHEMA: "revision_id",
        OPPORTUNITY_SCHEMA: "revision_id",
        EVENT_SCHEMA: "id",
        PLAN_SCHEMA: "revision_id",
        PROFILE_SCHEMA: "subject_id",
        SEARCH_POLICY_SCHEMA: "subject_id",
        ARTIFACT_SCHEMA: "revision_id",
        CAMPAIGN_SCHEMA: "revision_id",
        ACTION_SCHEMA: "revision_id",
    }.get(schema)
    value = record.value.get(key) if key else None
    return (schema, value) if isinstance(value, str) else None


def validate_revision_chain(
    records: Sequence[LoadedRecord],
    entity_key: str,
    revision_key: str,
    supersedes_key: str,
    diagnostics: list[Diagnostic],
) -> None:
    grouped: dict[str, list[LoadedRecord]] = defaultdict(list)
    for record in records:
        entity_id = record.value.get(entity_key)
        if isinstance(entity_id, str):
            grouped[entity_id].append(record)
    seen_revisions: set[str] = set()
    for entity_id, revisions in sorted(grouped.items()):
        tail: str | None = None
        for index, record in enumerate(revisions):
            revision_id = record.value.get(revision_key)
            supersedes = record.value.get(supersedes_key)
            if isinstance(revision_id, str):
                if revision_id in seen_revisions:
                    diag(
                        diagnostics,
                        record,
                        "error",
                        "revision.duplicate_id",
                        f"$.{revision_key}",
                        "revision identifier is reused",
                    )
                seen_revisions.add(revision_id)
            expected = None if index == 0 else tail
            if supersedes != expected:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "revision.branch_or_gap",
                    f"$.{supersedes_key}",
                    f"expected {expected!r} for the next revision of {entity_id}",
                )
            if isinstance(revision_id, str):
                tail = revision_id


def captured_time_by_evidence(records: Sequence[LoadedRecord]) -> dict[str, datetime]:
    result: dict[str, datetime] = {}
    for record in records:
        value = record.value
        evidence_id = value.get("id")
        source = value.get("source")
        captured = parse_time(source.get("captured_at")) if isinstance(source, dict) else None
        if isinstance(evidence_id, str) and captured is not None:
            result[evidence_id] = captured
    return result


def canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return value.strip()
    if not parts.scheme or not parts.netloc:
        return value.strip()
    kept = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"ref", "source"}
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(kept), ""))


def validate_cross_records(
    records: Sequence[LoadedRecord],
    diagnostics: list[Diagnostic],
    as_of: datetime | None = None,
) -> None:
    by_schema: dict[str, list[LoadedRecord]] = defaultdict(list)
    primary_ids: dict[tuple[str, str], LoadedRecord] = {}
    for record in records:
        schema = record.value.get("schema")
        if isinstance(schema, str):
            by_schema[schema].append(record)
        primary = record_primary_id(record)
        if primary is not None:
            if primary in primary_ids:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "record.duplicate_id",
                    "$",
                    f"identifier already appears at {primary_ids[primary].file}:{primary_ids[primary].line}",
                )
            else:
                primary_ids[primary] = record

    evidence_records = by_schema[EVIDENCE_SCHEMA]
    fact_records = by_schema[FACT_SCHEMA]
    opportunity_records = by_schema[OPPORTUNITY_SCHEMA]
    event_records = by_schema[EVENT_SCHEMA]
    plan_records = by_schema[PLAN_SCHEMA]
    profile_records = by_schema[PROFILE_SCHEMA]
    search_policy_records = by_schema[SEARCH_POLICY_SCHEMA]
    evidence_ids = {
        item.value.get("id") for item in evidence_records if isinstance(item.value.get("id"), str)
    }
    evidence_source_kind = {
        item.value["id"]: item.value.get("source", {}).get("kind")
        for item in evidence_records
        if isinstance(item.value.get("id"), str)
        and isinstance(item.value.get("source"), dict)
    }
    evidence_times = captured_time_by_evidence(evidence_records)
    opportunity_ids = {
        item.value.get("opportunity_id")
        for item in opportunity_records
        if isinstance(item.value.get("opportunity_id"), str)
    }
    profile_subject_ids = {
        item.value.get("subject_id")
        for item in profile_records
        if isinstance(item.value.get("subject_id"), str)
    }
    search_policy_subject_ids = {
        item.value.get("subject_id")
        for item in search_policy_records
        if isinstance(item.value.get("subject_id"), str)
    }
    if profile_subject_ids and search_policy_subject_ids and profile_subject_ids != search_policy_subject_ids:
        for record in search_policy_records:
            diag(
                diagnostics,
                record,
                "error",
                "workspace.subject_mismatch",
                "$.subject_id",
                "profile and search policy must describe the same subject",
            )

    validate_revision_chain(
        fact_records, "fact_id", "revision_id", "supersedes_revision_id", diagnostics
    )
    validate_revision_chain(
        opportunity_records,
        "opportunity_id",
        "revision_id",
        "supersedes_revision_id",
        diagnostics,
    )
    validate_revision_chain(
        plan_records, "plan_id", "revision_id", "supersedes_revision_id", diagnostics
    )
    artifact_records = by_schema[ARTIFACT_SCHEMA]
    campaign_records = by_schema[CAMPAIGN_SCHEMA]
    action_records = by_schema[ACTION_SCHEMA]
    validate_revision_chain(
        artifact_records, "artifact_id", "revision_id", "supersedes_revision_id", diagnostics
    )
    validate_revision_chain(
        campaign_records, "campaign_id", "revision_id", "supersedes_revision_id", diagnostics
    )
    validate_revision_chain(
        action_records, "action_id", "revision_id", "supersedes_revision_id", diagnostics
    )

    for record in fact_records + opportunity_records + event_records + artifact_records + action_records:
        recorded = parse_time(record.value.get("recorded_at"))
        evidence_refs: list[str] = []
        raw_refs = record.value.get("evidence_ids")
        if isinstance(raw_refs, list):
            evidence_refs.extend(item for item in raw_refs if isinstance(item, str))
        if record.value.get("schema") == OPPORTUNITY_SCHEMA:
            for origin in record.value.get("origins", []):
                if isinstance(origin, dict) and isinstance(origin.get("evidence_id"), str):
                    evidence_refs.append(origin["evidence_id"])
        if record.value.get("schema") == EVENT_SCHEMA:
            effect_result = record.value.get("effect_result")
            if isinstance(effect_result, dict) and isinstance(effect_result.get("provider_receipt"), str):
                evidence_refs.append(effect_result["provider_receipt"])
            if record.value.get("type") == "application_submitted":
                resolved = {
                    evidence_id
                    for evidence_id in raw_refs if isinstance(evidence_id, str)
                } & evidence_ids if isinstance(raw_refs, list) else set()
                if not resolved:
                    diag(
                        diagnostics,
                        record,
                        "error",
                        "event.application_evidence_unresolved",
                        "$.evidence_ids",
                        "application_submitted requires at least one evidence identifier that resolves in this workspace",
                    )
            if (
                isinstance(effect_result, dict)
                and effect_result.get("outcome") == "succeeded"
                and isinstance(effect_result.get("provider_receipt"), str)
                and effect_result["provider_receipt"] not in evidence_ids
            ):
                diag(
                    diagnostics,
                    record,
                    "error",
                    "event.succeeded_receipt_unresolved",
                    "$.effect_result.provider_receipt",
                    "the succeeded effect provider receipt must resolve in this workspace",
                )
        for evidence_id in evidence_refs:
            if evidence_id not in evidence_ids:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "reference.missing_evidence",
                    "$.evidence_ids",
                    f"missing evidence record {evidence_id}",
                )
            captured = evidence_times.get(evidence_id)
            if recorded is not None and captured is not None and captured > recorded:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "reference.future_evidence",
                    "$.evidence_ids",
                    f"{evidence_id} was captured after the citing record",
                )

    fact_ids = {
        item.value.get("fact_id") for item in fact_records if isinstance(item.value.get("fact_id"), str)
    }
    artifact_ids = {
        item.value.get("artifact_id") for item in artifact_records if isinstance(item.value.get("artifact_id"), str)
    }
    for record in artifact_records:
        opportunity_id = record.value.get("opportunity_id")
        if isinstance(opportunity_id, str) and opportunity_id not in opportunity_ids:
            diag(diagnostics, record, "error", "reference.missing_opportunity", "$.opportunity_id", f"missing opportunity record {opportunity_id}")
        for fact_id in record.value.get("source_fact_ids", []):
            if fact_id not in fact_ids:
                diag(diagnostics, record, "error", "artifact.missing_fact", "$.source_fact_ids", f"missing fact {fact_id}")
        for artifact_id in record.value.get("derived_from_artifact_ids", []):
            if artifact_id not in artifact_ids:
                diag(diagnostics, record, "error", "artifact.missing_parent", "$.derived_from_artifact_ids", f"missing artifact {artifact_id}")

    action_ids = {
        item.value.get("action_id") for item in action_records if isinstance(item.value.get("action_id"), str)
    }
    for record in action_records:
        opportunity_id = record.value.get("opportunity_id")
        if isinstance(opportunity_id, str) and opportunity_id not in opportunity_ids:
            diag(diagnostics, record, "error", "reference.missing_opportunity", "$.opportunity_id", f"missing opportunity record {opportunity_id}")
        for action_id in record.value.get("depends_on_action_ids", []):
            if action_id not in action_ids:
                diag(diagnostics, record, "error", "action.missing_dependency", "$.depends_on_action_ids", f"missing action {action_id}")

    fact_records_by_id: dict[str, LoadedRecord] = {}
    for record in fact_records:
        fact_id = record.value.get("fact_id")
        if isinstance(fact_id, str):
            fact_records_by_id[fact_id] = record
    for record in fact_records:
        source_id = record.value.get("fact_id")
        source_key = (
            record.value.get("subject_id"),
            record.value.get("predicate"),
            canonical_json(record.value.get("scope", {})),
        )
        for target_id in record.value.get("contradicts_fact_ids", []):
            target = fact_records_by_id.get(target_id)
            if target is None:
                diag(diagnostics, record, "error", "fact.missing_contradiction_target", "$.contradicts_fact_ids", f"missing fact {target_id}")
                continue
            target_key = (
                target.value.get("subject_id"),
                target.value.get("predicate"),
                canonical_json(target.value.get("scope", {})),
            )
            if source_key != target_key:
                diag(diagnostics, record, "error", "fact.cross_key_contradiction", "$.contradicts_fact_ids", f"{source_id} and {target_id} do not assert the same scoped predicate")

    fact_tails: dict[str, LoadedRecord] = {}
    for record in fact_records:
        fact_id = record.value.get("fact_id")
        if isinstance(fact_id, str):
            fact_tails[fact_id] = record
    active_by_key: dict[tuple[str, str, str], list[LoadedRecord]] = defaultdict(list)
    for record in fact_tails.values():
        value = record.value
        if value.get("operation") != "assert":
            continue
        key = (
            str(value.get("subject_id")),
            str(value.get("predicate")),
            canonical_json(value.get("scope", {})),
        )
        active_by_key[key].append(record)
    for key, active in sorted(active_by_key.items()):
        distinct = {canonical_json(item.value.get("value")) for item in active}
        if len(distinct) <= 1:
            continue
        fact_ids = {str(item.value.get("fact_id")) for item in active}
        linked: set[tuple[str, str]] = set()
        for item in active:
            source_id = str(item.value.get("fact_id"))
            for target in item.value.get("contradicts_fact_ids", []):
                linked.add(tuple(sorted((source_id, str(target)))))
        expected_pairs = {
            tuple(sorted((left, right)))
            for left in fact_ids
            for right in fact_ids
            if left < right
        }
        missing = expected_pairs - linked
        if missing:
            first = active[0]
            diag(
                diagnostics,
                first,
                "error",
                "fact.undeclared_conflict",
                "$",
                f"active unequal facts for {key[1]} require explicit contradiction links",
            )
        else:
            first = active[0]
            diag(
                diagnostics,
                first,
                "warning",
                "fact.disputed",
                "$",
                f"active facts for {key[1]} are explicitly disputed",
            )

    origin_owner: dict[tuple[str, str], str] = {}
    url_owners: dict[str, set[str]] = defaultdict(set)
    opportunity_tails: dict[str, LoadedRecord] = {}
    for record in opportunity_records:
        opportunity_id = record.value.get("opportunity_id")
        if isinstance(opportunity_id, str):
            opportunity_tails[opportunity_id] = record
    for opportunity_id, record in sorted(opportunity_tails.items()):
        for origin in record.value.get("origins", []):
            if not isinstance(origin, dict):
                continue
            provider_id = origin.get("provider_id")
            external_id = origin.get("external_id")
            if isinstance(provider_id, str) and isinstance(external_id, str) and external_id:
                key = (provider_id, external_id)
                owner = origin_owner.get(key)
                if owner is not None and owner != opportunity_id:
                    diag(
                        diagnostics,
                        record,
                        "error",
                        "opportunity.origin_collision",
                        "$.origins",
                        f"origin {provider_id}/{external_id} also maps to {owner}",
                    )
                origin_owner[key] = opportunity_id
            url = origin.get("url")
            if isinstance(url, str) and url:
                url_owners[canonical_url(url)].add(opportunity_id)
    for url, owners in sorted(url_owners.items()):
        if len(owners) > 1:
            owner = sorted(owners)[0]
            record = opportunity_tails[owner]
            diag(
                diagnostics,
                record,
                "warning",
                "opportunity.canonical_url_duplicate",
                "$.origins",
                f"canonical URL appears on multiple opportunities: {', '.join(sorted(owners))}",
            )

    event_ids: dict[str, LoadedRecord] = {}
    execution_state: dict[str, tuple[str, str]] = {}
    reconciliations_by_target: dict[str, tuple[str, str]] = {}
    event_tail: dict[str, tuple[str, str]] = {}
    for record in event_records:
        value = record.value
        event_id = value.get("id")
        opportunity_id = value.get("opportunity_id")
        if isinstance(event_id, str):
            event_ids[event_id] = record
        if not isinstance(opportunity_id, str):
            continue
        if opportunity_id not in opportunity_ids:
            diag(
                diagnostics,
                record,
                "error",
                "reference.missing_opportunity",
                "$.opportunity_id",
                f"missing opportunity record {opportunity_id}",
            )
        previous_tail = event_tail.get(opportunity_id)
        expected_previous = previous_tail[0] if previous_tail else None
        expected_status = previous_tail[1] if previous_tail else None
        if value.get("previous_event_id") != expected_previous:
            diag(
                diagnostics,
                record,
                "error",
                "event.tail_mismatch",
                "$.previous_event_id",
                f"expected {expected_previous!r}",
            )
        if value.get("status_before") != expected_status:
            diag(
                diagnostics,
                record,
                "error",
                "event.status_before_mismatch",
                "$.status_before",
                f"expected {expected_status!r}",
            )
        before = value.get("status_before")
        after = value.get("status_after")
        event_type = value.get("type")
        correction = value.get("correction_of_event_id")
        if before == "closed" and event_type not in {"correction", "reopened"}:
            diag(
                diagnostics,
                record,
                "error",
                "event.after_closed",
                "$.type",
                "events after closed require an explicit correction or reopen",
            )
        if before in STAGES and after in STAGES and STAGES.index(after) < STAGES.index(before):
            if event_type not in {"correction", "reopened"} or correction is None:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "event.regression_without_correction",
                    "$.status_after",
                    "stage regression requires a correction or reopen event with evidence",
                )
        if isinstance(correction, str):
            target = event_ids.get(correction)
            if target is None:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "event.missing_correction_target",
                    "$.correction_of_event_id",
                    f"missing prior event {correction}",
                )
            elif target.value.get("opportunity_id") != opportunity_id:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "event.cross_opportunity_correction",
                    "$.correction_of_event_id",
                    "correction target belongs to another opportunity",
                )
        effect_result = value.get("effect_result")
        if isinstance(effect_result, dict):
            plan_id = effect_result.get("plan_id")
            result = effect_result.get("outcome")
            if isinstance(plan_id, str) and isinstance(result, str):
                prior = execution_state.get(plan_id)
                if prior is not None and prior[0] == "ambiguous":
                    diag(diagnostics, record, "error", "event.ambiguous_retry", "$.effect_result", f"ambiguous execution {prior[1]} must be reconciled before another attempt")
                if prior is not None and prior[0] == "occurred":
                    diag(diagnostics, record, "error", "event.effect_already_occurred", "$.effect_result", "effect is already known to have occurred")
                execution_state[plan_id] = (result, str(event_id))
        reconciliation = value.get("effect_reconciliation")
        if isinstance(reconciliation, dict):
            plan_id = reconciliation.get("plan_id")
            target_id = reconciliation.get("ambiguous_event_id")
            target = event_ids.get(target_id)
            resolution = reconciliation.get("resolution")
            binding_valid = True
            prior_reconciliation = (
                reconciliations_by_target.get(target_id)
                if isinstance(target_id, str)
                else None
            )
            if prior_reconciliation is not None:
                prior_resolution, prior_event_id = prior_reconciliation
                code = (
                    "event.contradictory_reconciliation"
                    if resolution != prior_resolution
                    else "event.duplicate_reconciliation"
                )
                diag(
                    diagnostics,
                    record,
                    "error",
                    code,
                    "$.effect_reconciliation.ambiguous_event_id",
                    f"ambiguous execution {target_id} already has terminal reconciliation {prior_event_id}",
                )
                binding_valid = False
            elif isinstance(target_id, str) and resolution in {"occurred", "not_occurred"}:
                reconciliations_by_target[target_id] = (resolution, str(event_id))
            if target is None:
                diag(diagnostics, record, "error", "event.missing_ambiguous_event", "$.effect_reconciliation.ambiguous_event_id", f"missing prior event {target_id}")
                binding_valid = False
            else:
                target_result = target.value.get("effect_result")
                if (
                    target.value.get("type") != "effect_executed"
                    or not isinstance(target_result, dict)
                    or target_result.get("outcome") != "ambiguous"
                ):
                    diag(diagnostics, record, "error", "event.reconciliation_target_not_ambiguous", "$.effect_reconciliation.ambiguous_event_id", "target must be an ambiguous execution event")
                    binding_valid = False
                if isinstance(target_result, dict):
                    bindings = (
                        ("plan_id", "event.reconciliation_plan_mismatch", "plan"),
                        ("plan_revision_id", "event.reconciliation_revision_mismatch", "plan revision"),
                        ("approval_hash", "event.reconciliation_hash_mismatch", "approval hash"),
                    )
                    for key, code, label in bindings:
                        if reconciliation.get(key) != target_result.get(key):
                            diag(
                                diagnostics,
                                record,
                                "error",
                                code,
                                f"$.effect_reconciliation.{key}",
                                f"reconciliation and ambiguous event must reference the same {label}",
                            )
                            binding_valid = False
                if target.value.get("opportunity_id") != opportunity_id:
                    diag(
                        diagnostics,
                        record,
                        "error",
                        "event.reconciliation_opportunity_mismatch",
                        "$.opportunity_id",
                        "reconciliation and ambiguous event must reference the same opportunity",
                    )
                    binding_valid = False
            if (
                binding_valid
                and isinstance(plan_id, str)
                and resolution in {"occurred", "not_occurred"}
            ):
                execution_state[plan_id] = (
                    "occurred" if resolution == "occurred" else "reconciled_not_occurred",
                    str(event_id),
                )
        if isinstance(event_id, str) and isinstance(after, str):
            event_tail[opportunity_id] = (event_id, after)

    plan_by_revision: dict[str, LoadedRecord] = {}
    plan_revisions_by_id: dict[str, list[LoadedRecord]] = defaultdict(list)
    plan_basis_by_id: dict[str, str] = {}
    idempotency_basis: dict[str, str] = {}
    for record in plan_records:
        value = record.value
        revision_id = value.get("revision_id")
        if isinstance(revision_id, str):
            plan_by_revision[revision_id] = record
        plan_id = value.get("plan_id")
        if isinstance(plan_id, str):
            plan_revisions_by_id[plan_id].append(record)
        basis_hash = canonical_sha256(approval_basis(value))
        if isinstance(plan_id, str):
            prior_basis = plan_basis_by_id.get(plan_id)
            if prior_basis is not None and prior_basis != basis_hash:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "plan.basis_changed_in_revision",
                    "$",
                    "effect basis changed; create a new plan identifier",
                )
            plan_basis_by_id[plan_id] = basis_hash
        effect = value.get("effect")
        key = effect.get("idempotency_key") if isinstance(effect, dict) else None
        if isinstance(key, str):
            prior = idempotency_basis.get(key)
            if prior is not None and prior != basis_hash:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "plan.idempotency_reuse",
                    "$.effect.idempotency_key",
                    "idempotency key is bound to a different approval basis",
                )
            idempotency_basis[key] = basis_hash

    for plan_id, revisions in sorted(plan_revisions_by_id.items()):
        prior_time: datetime | None = None
        for revision in revisions:
            revision_time = parse_time(revision.value.get("recorded_at"))
            if prior_time is not None and revision_time is not None and revision_time < prior_time:
                diag(diagnostics, revision, "error", "plan.revision_time_regression", "$.recorded_at", f"plan {plan_id} revision time regressed")
            if revision_time is not None:
                prior_time = revision_time

    for record in event_records:
        effect_result = record.value.get("effect_result")
        if not isinstance(effect_result, dict):
            continue
        revision_id = effect_result.get("plan_revision_id")
        plan = plan_by_revision.get(revision_id)
        if plan is None:
            diag(
                diagnostics,
                record,
                "error",
                "event.missing_plan_revision",
                "$.effect_result.plan_revision_id",
                f"missing plan revision {revision_id}",
            )
            continue
        if effect_result.get("plan_id") != plan.value.get("plan_id"):
            diag(
                diagnostics,
                record,
                "error",
                "event.plan_id_mismatch",
                "$.effect_result.plan_id",
                "execution result is bound to a different plan",
            )
        if effect_result.get("approval_hash") != plan.value.get("approval_hash"):
            diag(
                diagnostics,
                record,
                "error",
                "event.plan_hash_mismatch",
                "$.effect_result.approval_hash",
                "execution result hash does not match the referenced plan revision",
            )
        if plan.value.get("opportunity_id") != record.value.get("opportunity_id"):
            diag(
                diagnostics,
                record,
                "error",
                "event.plan_opportunity_mismatch",
                "$.opportunity_id",
                "execution event and referenced plan must belong to the same opportunity",
            )
        effect = plan.value.get("effect")
        provider_receipt = effect_result.get("provider_receipt")
        if (
            effect_result.get("outcome") == "succeeded"
            and isinstance(effect, dict)
            and effect.get("action") == "submit_application"
            and provider_receipt in evidence_ids
            and evidence_source_kind.get(provider_receipt) not in {"provider_record", "email"}
        ):
            diag(
                diagnostics,
                record,
                "error",
                "event.submission_receipt_not_provider_acknowledgement",
                "$.effect_result.provider_receipt",
                "a succeeded submit_application effect requires provider_record or email evidence",
            )
        execution_time = parse_time(record.value.get("effective_at"))
        plan_id = plan.value.get("plan_id")
        effective_revisions = [
            item
            for item in plan_revisions_by_id.get(plan_id, [])
            if execution_time is not None
            and parse_time(item.value.get("recorded_at")) is not None
            and parse_time(item.value.get("recorded_at")) <= execution_time
        ]
        latest_plan = effective_revisions[-1] if effective_revisions else None
        if latest_plan is None or latest_plan.value.get("revision_id") != revision_id:
            diag(diagnostics, record, "error", "event.plan_revision_not_current", "$.effect_result.plan_revision_id", "execution must reference the latest plan revision recorded at effective_at")
        approval = plan.value.get("approval")
        approved_at = parse_time(approval.get("approved_at")) if isinstance(approval, dict) else None
        expires_at = parse_time(plan.value.get("expires_at"))
        if (
            not isinstance(approval, dict)
            or approval.get("state") != "approved"
            or execution_time is None
            or approved_at is None
            or execution_time < approved_at
            or expires_at is None
            or execution_time >= expires_at
        ):
            diag(
                diagnostics,
                record,
                "error",
                "event.plan_not_approved",
                "$.effect_result",
                "execution result lacks a current approval valid at effective_at",
            )

    opportunity_by_revision = {
        item.value.get("revision_id"): item
        for item in opportunity_records
        if isinstance(item.value.get("revision_id"), str)
    }
    artifact_by_revision = {
        item.value.get("revision_id"): item
        for item in artifact_records
        if isinstance(item.value.get("revision_id"), str)
    }
    action_ids = {
        item.value.get("action_id")
        for item in action_records
        if isinstance(item.value.get("action_id"), str)
    }
    for record in campaign_records:
        value = record.value
        workspace_tail = value.get("workspace_tail")
        if isinstance(workspace_tail, dict):
            if workspace_tail.get("profile_subject_id") not in profile_subject_ids:
                diag(diagnostics, record, "error", "campaign.profile_tail_mismatch", "$.workspace_tail.profile_subject_id", "workspace tail does not identify the loaded profile")
            if workspace_tail.get("search_policy_subject_id") not in search_policy_subject_ids:
                diag(diagnostics, record, "error", "campaign.policy_tail_mismatch", "$.workspace_tail.search_policy_subject_id", "workspace tail does not identify the loaded search policy")
            for index, revision_id in enumerate(workspace_tail.get("opportunity_revision_ids", [])):
                if revision_id not in opportunity_by_revision:
                    diag(diagnostics, record, "error", "campaign.missing_tail_opportunity", f"$.workspace_tail.opportunity_revision_ids[{index}]", f"missing opportunity revision {revision_id}")
            for index, event_id in enumerate(workspace_tail.get("pipeline_tail_event_ids", [])):
                if event_id not in event_ids:
                    diag(diagnostics, record, "error", "campaign.missing_tail_event", f"$.workspace_tail.pipeline_tail_event_ids[{index}]", f"missing pipeline event {event_id}")
            for index, revision_id in enumerate(workspace_tail.get("artifact_revision_ids", [])):
                if revision_id not in artifact_by_revision:
                    diag(diagnostics, record, "error", "campaign.missing_tail_artifact", f"$.workspace_tail.artifact_revision_ids[{index}]", f"missing artifact revision {revision_id}")
        tail_opportunity_revisions = set(workspace_tail.get("opportunity_revision_ids", [])) if isinstance(workspace_tail, dict) else set()
        allowed_accounts = set(value.get("allowed_account_ids", []))
        source_policy = value.get("source_policy")
        allowed_providers = set(source_policy.get("allowed_provider_ids", [])) if isinstance(source_policy, dict) else set()
        allowed_domains = {
            item.lower().lstrip(".")
            for item in (source_policy.get("allowed_domains", []) if isinstance(source_policy, dict) else [])
            if isinstance(item, str)
        }
        for index, item in enumerate(value.get("items", [])):
            if not isinstance(item, dict):
                continue
            base = f"$.items[{index}]"
            opportunity_id = item.get("opportunity_id")
            if opportunity_id not in opportunity_ids:
                diag(diagnostics, record, "error", "campaign.missing_opportunity", f"{base}.opportunity_id", f"missing opportunity {opportunity_id}")
            opportunity_revision_id = item.get("opportunity_revision_id")
            opportunity = opportunity_by_revision.get(opportunity_revision_id)
            if opportunity is None:
                diag(diagnostics, record, "error", "campaign.missing_opportunity_revision", f"{base}.opportunity_revision_id", f"missing opportunity revision {opportunity_revision_id}")
            else:
                opportunity_value = opportunity.value
                if opportunity_value.get("opportunity_id") != opportunity_id:
                    diag(diagnostics, record, "error", "campaign.opportunity_revision_mismatch", f"{base}.opportunity_revision_id", "revision belongs to another opportunity")
                application = opportunity_value.get("application")
                application_url = application.get("canonical_url") if isinstance(application, dict) else None
                if item.get("canonical_url") != application_url:
                    diag(diagnostics, record, "error", "campaign.canonical_url_mismatch", f"{base}.canonical_url", "item URL must match its exact opportunity revision")
                organization = opportunity_value.get("organization")
                organization_name = organization.get("name") if isinstance(organization, dict) else None
                if item.get("organization") != organization_name:
                    diag(diagnostics, record, "error", "campaign.organization_mismatch", f"{base}.organization", "item organization must match its exact opportunity revision")
                if item.get("title") != opportunity_value.get("title"):
                    diag(diagnostics, record, "error", "campaign.title_mismatch", f"{base}.title", "item title must match its exact opportunity revision")
                providers = {
                    origin.get("provider_id")
                    for origin in opportunity_value.get("origins", [])
                    if isinstance(origin, dict) and isinstance(origin.get("provider_id"), str)
                }
                hostname = (urlsplit(application_url).hostname or "").lower() if isinstance(application_url, str) else ""
                domain_allowed = any(hostname == domain or hostname.endswith("." + domain) for domain in allowed_domains)
                if not providers.intersection(allowed_providers) and not domain_allowed:
                    diag(diagnostics, record, "error", "campaign.source_not_allowed", base, "opportunity is outside the campaign source policy")
            if opportunity_revision_id not in tail_opportunity_revisions:
                diag(diagnostics, record, "error", "campaign.opportunity_not_in_tail", f"{base}.opportunity_revision_id", "item revision is not bound by workspace_tail")
            freshness_evidence_id = item.get("freshness_evidence_id")
            if freshness_evidence_id not in evidence_ids:
                diag(diagnostics, record, "error", "campaign.missing_freshness_evidence", f"{base}.freshness_evidence_id", f"missing evidence {freshness_evidence_id}")
            for dependency_index, action_id in enumerate(item.get("dependency_action_ids", [])):
                if action_id not in action_ids:
                    diag(diagnostics, record, "error", "campaign.missing_dependency_action", f"{base}.dependency_action_ids[{dependency_index}]", f"missing action {action_id}")
            revision_id = item.get("plan_revision_id")
            plan = None
            if revision_id is not None:
                plan = plan_by_revision.get(revision_id)
                if plan is None:
                    diag(diagnostics, record, "error", "campaign.missing_plan_revision", f"{base}.plan_revision_id", f"missing plan revision {revision_id}")
                else:
                    if item.get("plan_id") != plan.value.get("plan_id"):
                        diag(diagnostics, record, "error", "campaign.plan_id_mismatch", f"{base}.plan_id", "campaign item references a different plan")
                    if item.get("approval_hash") != plan.value.get("approval_hash"):
                        diag(diagnostics, record, "error", "campaign.plan_hash_mismatch", f"{base}.approval_hash", "campaign item hash does not match its plan")
                    if plan.value.get("opportunity_id") != opportunity_id:
                        diag(diagnostics, record, "error", "campaign.plan_opportunity_mismatch", base, "campaign plan belongs to another opportunity")
                    effect = plan.value.get("effect")
                    if isinstance(effect, dict):
                        if effect.get("action") != "submit_application":
                            diag(diagnostics, record, "error", "campaign.plan_action", f"{base}.plan_revision_id", "campaign plans must use the canonical submit_application action")
                        if effect.get("account_id") not in allowed_accounts:
                            diag(diagnostics, record, "error", "campaign.account_not_allowed", f"{base}.plan_revision_id", "plan account is outside the campaign allowlist")
            artifact_hashes: set[str] = set()
            for artifact_index, artifact_revision_id in enumerate(item.get("artifact_revision_ids", [])):
                artifact = artifact_by_revision.get(artifact_revision_id)
                if artifact is None:
                    diag(diagnostics, record, "error", "campaign.missing_artifact_revision", f"{base}.artifact_revision_ids[{artifact_index}]", f"missing artifact revision {artifact_revision_id}")
                    continue
                if artifact.value.get("opportunity_id") != opportunity_id:
                    diag(diagnostics, record, "error", "campaign.artifact_opportunity_mismatch", f"{base}.artifact_revision_ids[{artifact_index}]", "artifact belongs to another opportunity")
                if artifact.value.get("status") not in {"reviewed", "final", "submitted"}:
                    diag(diagnostics, record, "error", "campaign.artifact_not_reviewed", f"{base}.artifact_revision_ids[{artifact_index}]", "campaign artifacts must be reviewed or later")
                artifact_hash = artifact.value.get("sha256")
                if isinstance(artifact_hash, str):
                    artifact_hashes.add(artifact_hash)
            if plan is not None and artifact_hashes:
                effect = plan.value.get("effect")
                attachments = effect.get("attachments", []) if isinstance(effect, dict) else []
                attachment_hashes = {
                    attachment.get("sha256")
                    for attachment in attachments
                    if isinstance(attachment, dict) and isinstance(attachment.get("sha256"), str)
                }
                missing_hashes = sorted(artifact_hashes - attachment_hashes)
                if missing_hashes:
                    diag(diagnostics, record, "error", "campaign.artifact_plan_mismatch", f"{base}.artifact_revision_ids", "reviewed artifact hashes are absent from the exact effect plan")
            effect_event_id = item.get("effect_event_id")
            if effect_event_id is not None:
                event = event_ids.get(effect_event_id)
                if event is None:
                    diag(diagnostics, record, "error", "campaign.missing_effect_event", f"{base}.effect_event_id", f"missing event {effect_event_id}")
                else:
                    effect_result = event.value.get("effect_result")
                    expected_outcome = item.get("state")
                    if event.value.get("opportunity_id") != opportunity_id or event.value.get("type") != "effect_executed":
                        diag(diagnostics, record, "error", "campaign.effect_event_mismatch", f"{base}.effect_event_id", "receipt must be an effect_executed event for the same opportunity")
                    elif not isinstance(effect_result, dict):
                        diag(diagnostics, record, "error", "campaign.effect_result_missing", f"{base}.effect_event_id", "effect event lacks a structured result")
                    else:
                        if (
                            effect_result.get("plan_id") != item.get("plan_id")
                            or effect_result.get("plan_revision_id") != item.get("plan_revision_id")
                            or effect_result.get("approval_hash") != item.get("approval_hash")
                        ):
                            diag(diagnostics, record, "error", "campaign.effect_result_binding", f"{base}.effect_event_id", "effect result does not match the item's exact approved plan")
                        if effect_result.get("outcome") != expected_outcome:
                            diag(diagnostics, record, "error", "campaign.effect_outcome_mismatch", f"{base}.state", "item disposition must equal the execution outcome")
                        if expected_outcome == "succeeded" and event.value.get("status_after") != "applied":
                            diag(diagnostics, record, "error", "campaign.success_stage_mismatch", f"{base}.effect_event_id", "an acknowledged application submission must project status_after=applied")
                        if expected_outcome in {"failed", "ambiguous", "denied", "cancelled"} and event.value.get("status_after") != event.value.get("status_before"):
                            diag(diagnostics, record, "error", "campaign.failed_effect_advanced_stage", f"{base}.effect_event_id", "a non-successful application effect must not advance the pipeline")


def sort_diagnostics(diagnostics: Iterable[Diagnostic]) -> list[Diagnostic]:
    return sorted(
        diagnostics,
        key=lambda item: (
            item.file,
            item.line,
            item.json_path,
            item.code,
            item.severity,
            item.message,
        ),
    )


def validation_report(
    diagnostics: Sequence[Diagnostic],
    records: Sequence[LoadedRecord],
    strict_warnings: bool = False,
) -> dict[str, Any]:
    ordered = sort_diagnostics(diagnostics)
    errors = [asdict(item) for item in ordered if item.severity == "error"]
    warnings = [asdict(item) for item in ordered if item.severity == "warning"]
    schema_counts = Counter(
        str(record.value.get("schema", "missing")) for record in records
    )
    valid = not errors and not (strict_warnings and warnings)
    return {
        "schema": "career.validation_report.v1",
        "valid": valid,
        "strict_warnings": strict_warnings,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "records": len(records),
            "errors": len(errors),
            "warnings": len(warnings),
            "by_schema": dict(sorted(schema_counts.items())),
        },
    }


def workspace_record_paths(root: Path) -> list[Path]:
    paths = [root / name for name in LEDGER_SCHEMAS]
    paths.extend(root / name for name in WORKSPACE_SINGLE_SCHEMAS)
    paths.extend(root / name for name in WORKSPACE_NESTED_LEDGERS)
    effects = root / "plans" / "effects"
    if effects.is_dir():
        paths.extend(sorted(effects.rglob("*.json")))
        paths.extend(sorted(effects.rglob("*.jsonl")))
    campaigns = root / "plans" / "campaigns"
    if campaigns.is_dir():
        paths.extend(sorted(campaigns.rglob("*.json")))
        paths.extend(sorted(campaigns.rglob("*.jsonl")))
    return paths


def record_snapshot_time(record: LoadedRecord) -> datetime | None:
    """Return the time at which a record first belongs to a historical snapshot."""
    schema = record.value.get("schema")
    if schema == PROFILE_SCHEMA:
        return parse_time(record.value.get("created_at"))
    if schema == SEARCH_POLICY_SCHEMA:
        return parse_time(record.value.get("updated_at"))
    return parse_time(record.value.get("recorded_at"))


def load_workspace(
    root: Path,
    as_of: datetime | None = None,
) -> tuple[list[LoadedRecord], list[Diagnostic]]:
    records: list[LoadedRecord] = []
    diagnostics: list[Diagnostic] = []
    for name, expected_schema in WORKSPACE_SINGLE_SCHEMAS.items():
        path = root / name
        if not path.is_file():
            placeholder = LoadedRecord({}, path.as_posix(), 0)
            diag(diagnostics, placeholder, "error", "workspace.missing_record", "$", f"missing {name}")
            continue
        loaded, parse_diagnostics = read_records(path)
        diagnostics.extend(parse_diagnostics)
        if len(loaded) != 1:
            placeholder = loaded[0] if loaded else LoadedRecord({}, path.as_posix(), 0)
            diag(diagnostics, placeholder, "error", "workspace.single_record", "$", f"{name} requires exactly one record")
        for record in loaded:
            if record.value.get("schema") != expected_schema:
                diag(diagnostics, record, "error", "workspace.schema_mismatch", "$.schema", f"{name} accepts only {expected_schema}")
            records.append(record)
    for name, expected_schema in LEDGER_SCHEMAS.items():
        path = root / name
        if not path.is_file():
            placeholder = LoadedRecord({}, path.as_posix(), 0)
            diag(
                diagnostics,
                placeholder,
                "error",
                "workspace.missing_ledger",
                "$",
                f"missing {name}",
            )
            continue
        loaded, parse_diagnostics = read_records(path)
        diagnostics.extend(parse_diagnostics)
        for record in loaded:
            if record.value.get("schema") != expected_schema:
                diag(
                    diagnostics,
                    record,
                    "error",
                    "workspace.schema_mismatch",
                    "$.schema",
                    f"{name} accepts only {expected_schema}",
                )
            records.append(record)
    for name, expected_schema in WORKSPACE_NESTED_LEDGERS.items():
        path = root / name
        if not path.is_file():
            placeholder = LoadedRecord({}, path.as_posix(), 0)
            diag(diagnostics, placeholder, "error", "workspace.missing_ledger", "$", f"missing {name}")
            continue
        loaded, parse_diagnostics = read_records(path)
        diagnostics.extend(parse_diagnostics)
        for record in loaded:
            if record.value.get("schema") != expected_schema:
                diag(diagnostics, record, "error", "workspace.schema_mismatch", "$.schema", f"{name} accepts only {expected_schema}")
            records.append(record)
    effects = root / "plans" / "effects"
    if effects.is_dir():
        for path in sorted(list(effects.rglob("*.json")) + list(effects.rglob("*.jsonl"))):
            loaded, parse_diagnostics = read_records(path)
            diagnostics.extend(parse_diagnostics)
            for record in loaded:
                if record.value.get("schema") != PLAN_SCHEMA:
                    diag(
                        diagnostics,
                        record,
                        "error",
                        "workspace.schema_mismatch",
                        "$.schema",
                        f"effect plan files accept only {PLAN_SCHEMA}",
                    )
                records.append(record)
    campaigns = root / "plans" / "campaigns"
    if campaigns.is_dir():
        for path in sorted(list(campaigns.rglob("*.json")) + list(campaigns.rglob("*.jsonl"))):
            loaded, parse_diagnostics = read_records(path)
            diagnostics.extend(parse_diagnostics)
            for record in loaded:
                if record.value.get("schema") != CAMPAIGN_SCHEMA:
                    diag(diagnostics, record, "error", "workspace.schema_mismatch", "$.schema", f"campaign files accept only {CAMPAIGN_SCHEMA}")
                records.append(record)
    if as_of is not None:
        records = [
            record
            for record in records
            if record_snapshot_time(record) is None or record_snapshot_time(record) <= as_of
        ]
    for record in records:
        validate_record_structure(record, diagnostics, as_of)
    validate_cross_records(records, diagnostics, as_of)
    return records, diagnostics


def print_report(report: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
        return
    counts = report["counts"]
    state = "PASS" if report["valid"] else "FAIL"
    print(
        f"Career data validation: {state} "
        f"({counts['records']} records, {counts['errors']} errors, "
        f"{counts['warnings']} warnings)"
    )
    for severity in ("errors", "warnings"):
        for item in report[severity]:
            print(
                f"{item['severity'].upper()} {item['file']}:{item['line']} "
                f"{item['json_path']} {item['code']}: {item['message']}"
            )


def parse_as_of(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = parse_time(value)
    if parsed is None:
        raise SystemExit("--as-of must be an RFC 3339 timestamp with timezone")
    return parsed


def cmd_validate(args: argparse.Namespace) -> int:
    target = Path(args.target)
    as_of = parse_as_of(args.as_of)
    if target.is_dir():
        records, diagnostics = load_workspace(target, as_of)
    elif target.is_file():
        records, diagnostics = read_records(target)
        for record in records:
            validate_record_structure(record, diagnostics, as_of)
    else:
        print(f"target does not exist: {target}", file=sys.stderr)
        return 2
    report = validation_report(diagnostics, records, args.strict_warnings)
    print_report(report, args.json)
    return 0 if report["valid"] else 1


def write_json_if_missing(path: Path, value: Any) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return True


def cmd_init_workspace(args: argparse.Namespace) -> int:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    timestamp = args.timestamp or utc_now()
    if parse_time(timestamp) is None:
        print("--timestamp must be RFC 3339 with timezone", file=sys.stderr)
        return 2
    existing_subjects: set[str] = set()
    for name, expected_schema in WORKSPACE_SINGLE_SCHEMAS.items():
        path = root / name
        if not path.is_file():
            continue
        loaded, parse_diagnostics = read_records(path)
        if parse_diagnostics or len(loaded) != 1 or loaded[0].value.get("schema") != expected_schema:
            print(f"cannot safely extend invalid existing {name}; validate or repair it first", file=sys.stderr)
            return 1
        existing_subject = loaded[0].value.get("subject_id")
        if not typed_uuid(existing_subject, "subject"):
            print(f"cannot safely extend {name} with an invalid subject_id", file=sys.stderr)
            return 1
        existing_subjects.add(existing_subject)
    if len(existing_subjects) > 1:
        print("existing profile and search policy have different subject_id values", file=sys.stderr)
        return 1
    existing_subject_id = next(iter(existing_subjects), None)
    if args.subject_id is not None and existing_subject_id is not None and args.subject_id != existing_subject_id:
        print("--subject-id does not match the existing workspace subject", file=sys.stderr)
        return 1
    subject_id = args.subject_id or existing_subject_id or f"subject-{uuid.uuid4()}"
    if not typed_uuid(subject_id, "subject"):
        print("--subject-id must be subject-<uuid>", file=sys.stderr)
        return 2
    profile = {
        "schema": "career.profile.v1",
        "subject_id": subject_id,
        "created_at": timestamp,
        "goals": [],
        "preferences": {
            "role_families": [],
            "workplace": [],
            "locations": [],
            "timezones": [],
            "employment_types": [],
        },
        "constraints": {"hard": [], "soft": [], "unknown": []},
        "retention": {
            "default_days": 90,
            "keep_evidence_until_review": True,
            "review_on": None,
        },
        "sharing": {"default": "local_only"},
    }
    search_policy = {
        "schema": "career.search_policy.v1",
        "subject_id": subject_id,
        "updated_at": timestamp,
        "role_families": [],
        "adjacent_titles": [],
        "hard_filters": [],
        "positive_signals": [],
        "avoid_signals": [],
        "authorized_sources": [],
        "source_queries": [],
        "freshness_days": 7,
        "review_cadence_days": 7,
        "result_budget_per_run": 50,
    }
    created: list[str] = []
    for name, value in (("profile.json", profile), ("search-policy.json", search_policy)):
        if write_json_if_missing(root / name, value):
            created.append(name)
    for name in LEDGER_SCHEMAS:
        path = root / name
        if not path.exists():
            path.write_text("", encoding="utf-8")
            created.append(name)
    for directory in (
        root / "artifacts",
        root / "plans" / "effects",
        root / "plans" / "campaigns",
        root / "archive",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    artifact_index = root / "artifacts" / "index.jsonl"
    if not artifact_index.exists():
        artifact_index.write_text("", encoding="utf-8")
        created.append("artifacts/index.jsonl")
    runtime_readme = root / "README.md"
    if not runtime_readme.exists():
        runtime_readme.write_text(
            "# Private Career Data\n\n"
            "This directory is user-owned runtime state. Keep it private, review "
            "retention regularly, and do not commit it to a public repository.\n",
            encoding="utf-8",
        )
        created.append("README.md")
    print(json.dumps({"root": str(root), "created": created, "preserved": not bool(created)}, indent=2))
    return 0


def semantic_records(path: Path) -> tuple[list[str], list[Diagnostic]]:
    records, diagnostics = read_records(path)
    return [canonical_json(record.value) for record in records], diagnostics


def relative_core_files(root: Path) -> list[Path]:
    paths = [Path(name) for name in LEDGER_SCHEMAS]
    paths.extend(Path(name) for name in WORKSPACE_NESTED_LEDGERS)
    effects = root / "plans" / "effects"
    if effects.is_dir():
        paths.extend(path.relative_to(root) for path in sorted(effects.rglob("*.json")))
        paths.extend(path.relative_to(root) for path in sorted(effects.rglob("*.jsonl")))
    campaigns = root / "plans" / "campaigns"
    if campaigns.is_dir():
        paths.extend(path.relative_to(root) for path in sorted(campaigns.rglob("*.json")))
        paths.extend(path.relative_to(root) for path in sorted(campaigns.rglob("*.jsonl")))
    return sorted(set(paths), key=lambda item: item.as_posix())


def cmd_verify_append(args: argparse.Namespace) -> int:
    base = Path(args.base)
    candidate = Path(args.candidate)
    diagnostics: list[Diagnostic] = []
    checked = 0
    for relative in relative_core_files(base):
        old_path = base / relative
        new_path = candidate / relative
        placeholder = LoadedRecord({}, new_path.as_posix(), 0)
        if not new_path.is_file():
            diag(
                diagnostics,
                placeholder,
                "error",
                "append.missing_file",
                "$",
                f"candidate removed {relative.as_posix()}",
            )
            continue
        old_values, old_diags = semantic_records(old_path)
        new_values, new_diags = semantic_records(new_path)
        diagnostics.extend(old_diags)
        diagnostics.extend(new_diags)
        checked += 1
        if len(new_values) < len(old_values):
            diag(
                diagnostics,
                placeholder,
                "error",
                "append.truncated",
                "$",
                "candidate ledger is shorter than baseline",
            )
            continue
        for index, old_value in enumerate(old_values):
            if new_values[index] != old_value:
                diag(
                    diagnostics,
                    placeholder,
                    "error",
                    "append.prefix_changed",
                    f"$[{index}]",
                    "baseline record was edited, reordered, or displaced",
                )
                break
    report = validation_report(diagnostics, [], False)
    report["schema"] = "career.append_verification.v1"
    report["counts"]["files_checked"] = checked
    print_report(report, args.json)
    return 0 if report["valid"] else 1


def plan_executable(plan: dict[str, Any], as_of: datetime | None) -> tuple[bool | None, str]:
    approval = plan.get("approval")
    if not isinstance(approval, dict) or approval.get("state") != "approved":
        return False, "approval state is not approved"
    if plan.get("approval_hash") != canonical_sha256(approval_basis(plan)):
        return False, "approval hash does not match"
    if as_of is None:
        return None, "supply --as-of to evaluate approval time and expiry"
    created = parse_time(plan.get("created_at"))
    approved_at = parse_time(approval.get("approved_at"))
    expires = parse_time(plan.get("expires_at"))
    if created is None or approved_at is None or expires is None:
        return False, "plan timestamps are invalid"
    if not created <= approved_at <= as_of:
        return False, "plan is not yet approved at the supplied as-of time"
    if as_of >= expires:
        return False, "plan is expired at the supplied as-of time"
    return True, "approved, hash-bound, and unexpired"


def cmd_approval_hash(args: argparse.Namespace) -> int:
    path = Path(args.plan)
    records, diagnostics = read_records(path)
    as_of = parse_as_of(args.as_of)
    if len(records) != 1:
        print("approval-hash requires exactly one plan object", file=sys.stderr)
        return 2
    record = records[0]
    validate_record_structure(record, diagnostics, as_of)
    if record.value.get("schema") != PLAN_SCHEMA:
        report = validation_report(diagnostics, records)
        print_report(report, args.json)
        return 1
    expected = canonical_sha256(approval_basis(record.value))
    executable, reason = plan_executable(record.value, as_of)
    report = validation_report(diagnostics, records)
    payload = {
        "schema": "career.approval_hash_result.v1",
        "valid": report["valid"],
        "expected_hash": expected,
        "supplied_hash": record.value.get("approval_hash"),
        "executable": executable,
        "reason": reason,
        "errors": report["errors"],
        "warnings": report["warnings"],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(expected)
        print(f"executable={executable}: {reason}")
    return 0 if report["valid"] else 1


def current_projection(
    records: Sequence[LoadedRecord], as_of: datetime | None = None
) -> dict[str, Any]:
    fact_tail: dict[str, dict[str, Any]] = {}
    opportunity_tail: dict[str, dict[str, Any]] = {}
    event_tail: dict[str, dict[str, Any]] = {}
    event_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    evidence_kind: dict[str, str] = {}
    artifact_tail: dict[str, dict[str, Any]] = {}
    action_tail: dict[str, dict[str, Any]] = {}
    campaign_tail: dict[str, dict[str, Any]] = {}
    plan_action_by_revision: dict[str, str] = {}
    for record in records:
        value = record.value
        recorded = parse_time(value.get("recorded_at"))
        if as_of is not None and recorded is not None and recorded > as_of:
            continue
        if value.get("schema") == FACT_SCHEMA and isinstance(value.get("fact_id"), str):
            fact_tail[value["fact_id"]] = value
        elif value.get("schema") == OPPORTUNITY_SCHEMA and isinstance(value.get("opportunity_id"), str):
            opportunity_tail[value["opportunity_id"]] = value
        elif value.get("schema") == EVENT_SCHEMA and isinstance(value.get("opportunity_id"), str):
            event_tail[value["opportunity_id"]] = value
            event_history[value["opportunity_id"]].append(value)
        elif value.get("schema") == EVIDENCE_SCHEMA and isinstance(value.get("id"), str):
            source = value.get("source")
            if isinstance(source, dict) and isinstance(source.get("kind"), str):
                evidence_kind[value["id"]] = source["kind"]
        elif value.get("schema") == ARTIFACT_SCHEMA and isinstance(value.get("artifact_id"), str):
            artifact_tail[value["artifact_id"]] = value
        elif value.get("schema") == ACTION_SCHEMA and isinstance(value.get("action_id"), str):
            action_tail[value["action_id"]] = value
        elif value.get("schema") == CAMPAIGN_SCHEMA and isinstance(value.get("campaign_id"), str):
            campaign_tail[value["campaign_id"]] = value
        elif value.get("schema") == PLAN_SCHEMA and isinstance(value.get("revision_id"), str):
            effect = value.get("effect")
            if isinstance(effect, dict) and isinstance(effect.get("action"), str):
                plan_action_by_revision[value["revision_id"]] = effect["action"]

    def is_acknowledged_submission(event: dict[str, Any]) -> bool:
        effect_result = event.get("effect_result")
        if not isinstance(effect_result, dict):
            return False
        provider_receipt = effect_result.get("provider_receipt")
        return (
            event.get("type") == "effect_executed"
            and effect_result.get("outcome") == "succeeded"
            and plan_action_by_revision.get(effect_result.get("plan_revision_id"))
            == "submit_application"
            and evidence_kind.get(provider_receipt) in {"provider_record", "email"}
        )

    facts_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for value in fact_tail.values():
        if value.get("operation") == "assert":
            key = (
                value.get("subject_id", ""),
                value.get("predicate", ""),
                canonical_json(value.get("scope", {})),
            )
            facts_by_key[key].append(value)
    facts: list[dict[str, Any]] = []
    for (subject_id, predicate, scope_json), values in sorted(facts_by_key.items()):
        distinct = {canonical_json(item.get("value")) for item in values}
        facts.append(
            {
                "subject_id": subject_id,
                "predicate": predicate,
                "scope": strict_json_loads(scope_json),
                "state": "established" if len(distinct) == 1 else "disputed",
                "values": [
                    {"fact_id": item["fact_id"], "value": item.get("value"), "confidence": item.get("confidence")}
                    for item in sorted(values, key=lambda item: item["fact_id"])
                ],
            }
        )
    opportunities: list[dict[str, Any]] = []
    current_stage_counts = Counter()
    terminal_outcomes = Counter()
    milestone_sets: dict[str, set[str]] = {
        "discovered": set(),
        "application_submitted": set(),
        "screening": set(),
        "interviewing": set(),
        "offer": set(),
    }
    for opportunity_id, opportunity in sorted(opportunity_tail.items()):
        event = event_tail.get(opportunity_id)
        history = event_history.get(opportunity_id, [])
        provider_ack_events = [
            history_event
            for history_event in history
            if is_acknowledged_submission(history_event)
        ]
        for history_event in history:
            milestone_sets["discovered"].add(opportunity_id)
            event_type = history_event.get("type")
            stage = history_event.get("status_after")
            if event_type == "application_submitted" or is_acknowledged_submission(history_event):
                milestone_sets["application_submitted"].add(opportunity_id)
            if stage == "screening":
                milestone_sets["screening"].add(opportunity_id)
            if event_type in {"interview_scheduled", "interview_completed"} or stage == "interviewing":
                milestone_sets["interviewing"].add(opportunity_id)
            if event_type == "offer_received" or stage == "offer":
                milestone_sets["offer"].add(opportunity_id)
        application_events = [item for item in history if item.get("type") == "application_submitted"]
        provider_ack_event = provider_ack_events[-1] if provider_ack_events else None
        submission = application_events[-1] if application_events else provider_ack_event
        submission_evidence_ids = {
            evidence_id
            for evidence_id in (submission or {}).get("evidence_ids", [])
            if isinstance(evidence_id, str)
        }
        submission_kinds = {
            evidence_kind.get(evidence_id)
            for evidence_id in submission_evidence_ids
        }
        if submission is None:
            verification_basis = None
        elif provider_ack_event is not None:
            verification_basis = "provider_acknowledged"
        elif "user_statement" in submission_kinds:
            verification_basis = "user_reported"
        else:
            verification_basis = "documented_without_provider_acknowledgement"
        submitted_artifacts = [
            item
            for item in artifact_tail.values()
            if item.get("opportunity_id") == opportunity_id and item.get("status") == "submitted"
        ]
        status = event.get("status_after") if event else None
        if isinstance(status, str):
            current_stage_counts[status] += 1
        outcome = event.get("outcome") if event else None
        if isinstance(outcome, dict) and isinstance(outcome.get("kind"), str):
            terminal_outcomes[outcome["kind"]] += 1
        opportunities.append(
            {
                "opportunity_id": opportunity_id,
                "title": opportunity.get("title"),
                "organization": opportunity.get("organization"),
                "status": status,
                "outcome": outcome,
                "tail_event_id": event.get("id") if event else None,
                "ever_reached": sorted(
                    name for name, owners in milestone_sets.items() if opportunity_id in owners
                ),
                "submission_verification": {
                    "basis": verification_basis,
                    "remote_verified_at": provider_ack_event.get("effective_at") if provider_ack_event is not None else None,
                    "artifact_hash_known": bool(submitted_artifacts),
                    "verification_gap": (
                        None
                        if submission is None or (verification_basis == "provider_acknowledged" and submitted_artifacts)
                        else "provider acknowledgement or exact submitted artifact hash is missing"
                    ),
                },
            }
        )
    queue = []
    for action_id, action in sorted(action_tail.items()):
        if action.get("state") not in {"pending", "blocked"}:
            continue
        due = parse_time(action.get("due_at"))
        queue.append(
            {
                "action_id": action_id,
                "opportunity_id": action.get("opportunity_id"),
                "kind": action.get("kind"),
                "state": action.get("state"),
                "priority": action.get("priority"),
                "due_at": action.get("due_at"),
                "overdue": bool(as_of is not None and due is not None and due < as_of),
                "basis": action.get("basis"),
            }
        )
    queue.sort(key=lambda item: (not item["overdue"], item["due_at"] or "9999", item["action_id"]))
    campaigns = [
        {
            "campaign_id": value.get("campaign_id"),
            "name": value.get("name"),
            "state": value.get("state"),
            "target_count": value.get("target_count"),
            "roster_count": value.get("roster_count"),
            "counts": value.get("counts"),
        }
        for _, value in sorted(campaign_tail.items())
    ]
    return {
        "schema": "career.projection.v1",
        "as_of": as_of.isoformat() if as_of is not None else None,
        "facts": facts,
        "opportunities": opportunities,
        "metrics": {
            "current_stage_counts": dict(sorted(current_stage_counts.items())),
            "ever_reached": {key: len(value) for key, value in sorted(milestone_sets.items())},
            "terminal_outcomes": dict(sorted(terminal_outcomes.items())),
        },
        "campaigns": campaigns,
        "queue": queue,
    }


def cmd_project(args: argparse.Namespace) -> int:
    root = Path(args.root)
    as_of = parse_as_of(args.as_of)
    records, diagnostics = load_workspace(root, as_of)
    report = validation_report(diagnostics, records, args.strict_warnings)
    if not report["valid"]:
        print_report(report, args.json)
        return 1
    projection = current_projection(records, as_of)
    if args.opportunity:
        projection["opportunities"] = [
            item
            for item in projection["opportunities"]
            if item["opportunity_id"] == args.opportunity
        ]
    print(json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


def cmd_ops_brief(args: argparse.Namespace) -> int:
    root = Path(args.root)
    as_of = parse_as_of(args.as_of)
    if as_of is None:
        print("ops-brief requires --as-of for deterministic due and overdue state", file=sys.stderr)
        return 2
    records, diagnostics = load_workspace(root, as_of)
    report = validation_report(diagnostics, records, args.strict_warnings)
    if not report["valid"]:
        print_report(report, args.json)
        return 1
    projection = current_projection(records, as_of)
    unresolved_effects = []
    for record in records:
        value = record.value
        if value.get("schema") != EVENT_SCHEMA:
            continue
        effect_result = value.get("effect_result")
        if isinstance(effect_result, dict) and effect_result.get("outcome") == "ambiguous":
            unresolved_effects.append(
                {
                    "event_id": value.get("id"),
                    "opportunity_id": value.get("opportunity_id"),
                    "plan_id": effect_result.get("plan_id"),
                }
            )
        reconciliation = value.get("effect_reconciliation")
        if isinstance(reconciliation, dict):
            unresolved_effects = [
                item
                for item in unresolved_effects
                if item["event_id"] != reconciliation.get("ambiguous_event_id")
                or reconciliation.get("resolution") == "unknown"
            ]
    payload = {
        "schema": "career.ops_brief.v1",
        "as_of": args.as_of,
        "validation": report["counts"],
        "metrics": projection["metrics"],
        "campaigns": projection["campaigns"],
        "queue": projection["queue"],
        "ambiguous_effects": unresolved_effects,
        "next_action": projection["queue"][0] if projection["queue"] else None,
        "coverage_note": "Derived from the validated local workspace only; live providers were not refreshed.",
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


@contextlib.contextmanager
def exclusive_file_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def cmd_append_event(args: argparse.Namespace) -> int:
    root = Path(args.workspace)
    event_path = Path(args.event)
    incoming, incoming_diags = read_records(event_path)
    if len(incoming) != 1:
        print("append-event requires exactly one event object", file=sys.stderr)
        return 2
    event = incoming[0]
    expected_tail = None if args.expected_tail_id == "EMPTY" else args.expected_tail_id
    ledger = root / "pipeline-events.jsonl"
    with exclusive_file_lock(root / ".locks" / "pipeline-events.lock"):
        records, diagnostics = load_workspace(root, None)
        diagnostics.extend(incoming_diags)
        validate_record_structure(event, diagnostics)
        if event.value.get("schema") != EVENT_SCHEMA:
            report = validation_report(diagnostics, records + incoming)
            print_report(report, args.json)
            return 1
        opportunity_id = event.value.get("opportunity_id")
        existing_events = [
            record
            for record in records
            if record.value.get("schema") == EVENT_SCHEMA
            and record.value.get("opportunity_id") == opportunity_id
        ]
        actual_tail = existing_events[-1].value.get("id") if existing_events else None
        if expected_tail != actual_tail:
            print(f"tail changed: expected {expected_tail!r}, actual {actual_tail!r}", file=sys.stderr)
            return 1
        if event.value.get("previous_event_id") != actual_tail:
            print("event previous_event_id does not match the verified tail", file=sys.stderr)
            return 1
        combined = records + [
            LoadedRecord(event.value, ledger.as_posix(), len(existing_events) + 1)
        ]
        cross_diags: list[Diagnostic] = []
        validate_cross_records(combined, cross_diags)
        report = validation_report(diagnostics + cross_diags, combined)
        if not report["valid"]:
            print_report(report, args.json)
            return 1
        existing = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
        if existing and not existing.endswith("\n"):
            existing += "\n"
        updated = existing + canonical_json(event.value) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix="pipeline-events-", suffix=".tmp", dir=ledger.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, ledger)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    payload = {"appended": event.value.get("id"), "previous_event_id": actual_tail}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def parse_analysis(path: Path) -> dict[str, Any]:
    records, diagnostics = read_records(path)
    if diagnostics or len(records) != 1:
        raise ValueError("analysis must be one strict JSON object")
    return records[0].value


def percent(numerator: Decimal, denominator: Decimal) -> str | None:
    if denominator == 0:
        return None
    return str((numerator * Decimal("100") / denominator).quantize(Decimal("0.1")))


def cmd_score_fit(args: argparse.Namespace) -> int:
    try:
        analysis = parse_analysis(Path(args.analysis))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if analysis.get("schema") != "career.opportunity_analysis.v1":
        print("schema must be career.opportunity_analysis.v1", file=sys.stderr)
        return 1
    criteria = analysis.get("criteria")
    constraints = analysis.get("hard_constraints")
    if not isinstance(criteria, list) or not isinstance(constraints, list):
        print("criteria and hard_constraints arrays are required", file=sys.stderr)
        return 1
    total = Decimal(0)
    known = Decimal(0)
    matched = Decimal(0)
    breakdown: list[dict[str, Any]] = []
    factors = {"met": Decimal(1), "partial": Decimal("0.5"), "gap": Decimal(0)}
    try:
        for item in criteria:
            if not isinstance(item, dict):
                raise ValueError("each criterion must be an object")
            weight = item.get("weight")
            if isinstance(weight, bool) or not isinstance(weight, int) or not 1 <= weight <= 100:
                raise ValueError("criterion weight must be an integer from 1 to 100")
            assessment = item.get("assessment")
            if assessment not in {"met", "partial", "gap", "unknown"}:
                raise ValueError("criterion assessment is invalid")
            weight_d = Decimal(weight)
            total += weight_d
            contribution: Decimal | None = None
            if assessment != "unknown":
                known += weight_d
                contribution = weight_d * factors[assessment]
                matched += contribution
            breakdown.append(
                {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "importance": item.get("importance"),
                    "weight": weight,
                    "assessment": assessment,
                    "contribution": str(contribution) if contribution is not None else None,
                    "evidence_ids": item.get("evidence_ids", []),
                }
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    failed = [item for item in constraints if isinstance(item, dict) and item.get("assessment") == "fail"]
    unknown = [item for item in constraints if isinstance(item, dict) and item.get("assessment") == "unknown"]
    recommendation = (
        "do_not_proceed" if failed else "clarify" if unknown else "prioritize_with_user_judgment"
    )
    result = {
        "schema": "career.fit_score.v1",
        "opportunity_id": analysis.get("opportunity_id"),
        "recommendation_gate": recommendation,
        "hard_constraint_failures": failed,
        "hard_constraint_unknowns": unknown,
        "coverage_percent": percent(known, total),
        "priority_percent": percent(matched, total),
        "fit_on_known_percent": percent(matched, known),
        "weights_total": str(total),
        "weights_known": str(known),
        "weighted_match": str(matched),
        "criteria": breakdown,
        "interpretation": "Prioritization aid, not a hiring probability or legal eligibility decision.",
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


def cmd_validate_claims(args: argparse.Namespace) -> int:
    facts, fact_diags = read_records(Path(args.facts))
    evidence, evidence_diags = read_records(Path(args.evidence))
    manifests, manifest_diags = read_records(Path(args.manifest))
    diagnostics = fact_diags + evidence_diags + manifest_diags
    for record in facts + evidence:
        validate_record_structure(record, diagnostics)
    validate_cross_records(facts + evidence, diagnostics)
    if len(manifests) != 1:
        print("manifest must contain exactly one object", file=sys.stderr)
        return 2
    manifest = manifests[0]
    claims = manifest.value.get("claims")
    if manifest.value.get("schema") != "career.claim_manifest.v1" or not isinstance(claims, list):
        diag(
            diagnostics,
            manifest,
            "error",
            "claim.manifest",
            "$",
            "career.claim_manifest.v1 with a claims array required",
        )
        claims = []
    fact_tail: dict[str, dict[str, Any]] = {}
    for record in facts:
        fact_id = record.value.get("fact_id")
        if isinstance(fact_id, str):
            fact_tail[fact_id] = record.value
    for index, claim in enumerate(claims):
        path = f"$.claims[{index}]"
        if not isinstance(claim, dict):
            diag(diagnostics, manifest, "error", "claim.object", path, "object required")
            continue
        disposition = claim.get("disposition")
        if disposition not in {"supported", "needs_confirmation", "unsupported", "omit"}:
            diag(
                diagnostics,
                manifest,
                "error",
                "claim.disposition",
                f"{path}.disposition",
                "invalid disposition",
            )
            continue
        fact_ids = claim.get("fact_ids")
        if not isinstance(fact_ids, list) or not all(isinstance(item, str) for item in fact_ids):
            diag(
                diagnostics,
                manifest,
                "error",
                "claim.fact_ids",
                f"{path}.fact_ids",
                "fact identifier array required",
            )
            continue
        usable = []
        for fact_id in fact_ids:
            fact = fact_tail.get(fact_id)
            if fact is None:
                diag(
                    diagnostics,
                    manifest,
                    "error",
                    "claim.missing_fact",
                    f"{path}.fact_ids",
                    f"missing fact {fact_id}",
                )
            elif fact.get("operation") == "assert" and fact.get("confidence") in {"medium", "high"}:
                usable.append(fact)
        if disposition == "supported" and not usable:
            diag(
                diagnostics,
                manifest,
                "error",
                "claim.unsupported",
                path,
                "supported claim needs an active medium- or high-confidence fact",
            )
        if disposition in {"unsupported", "omit"} and claim.get("publish", False):
            diag(
                diagnostics,
                manifest,
                "error",
                "claim.quarantine_bypass",
                f"{path}.publish",
                "unsupported or omitted claim cannot be marked for publication",
            )
    report = validation_report(diagnostics, facts + evidence + manifests, args.strict_warnings)
    print_report(report, args.json)
    return 0 if report["valid"] else 1


def cmd_dedupe_opportunities(args: argparse.Namespace) -> int:
    records, diagnostics = read_records(Path(args.opportunities))
    for record in records:
        validate_record_structure(record, diagnostics)
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.value.get("schema") == OPPORTUNITY_SCHEMA:
            opportunity_id = record.value.get("opportunity_id")
            if isinstance(opportunity_id, str):
                latest[opportunity_id] = record.value
    origin_groups: dict[str, list[str]] = defaultdict(list)
    url_groups: dict[str, list[str]] = defaultdict(list)
    fingerprint_groups: dict[str, list[str]] = defaultdict(list)
    for opportunity_id, value in latest.items():
        for origin in value.get("origins", []):
            if not isinstance(origin, dict):
                continue
            if origin.get("external_id"):
                key = f"{origin.get('provider_id')}:{origin.get('external_id')}"
                origin_groups[key].append(opportunity_id)
            if origin.get("url"):
                url_groups[canonical_url(origin["url"])].append(opportunity_id)
        organization = value.get("organization", {})
        name = organization.get("name", "") if isinstance(organization, dict) else ""
        fingerprint = re.sub(r"[^a-z0-9]+", " ", f"{value.get('title', '')} {name}".lower()).strip()
        if fingerprint:
            fingerprint_groups[fingerprint].append(opportunity_id)
    only_duplicates = lambda groups: {
        key: sorted(set(values)) for key, values in sorted(groups.items()) if len(set(values)) > 1
    }
    report = {
        "schema": "career.dedupe_report.v1",
        "records": len(records),
        "current_opportunities": len(latest),
        "exact_origin_collisions": only_duplicates(origin_groups),
        "canonical_url_candidates": only_duplicates(url_groups),
        "title_organization_candidates": only_duplicates(fingerprint_groups),
        "note": "Candidate groups require review; this command never merges or deletes records.",
        "parse_or_structure_diagnostics": [asdict(item) for item in sort_diagnostics(diagnostics)],
    }
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def cmd_check_triggers(args: argparse.Namespace) -> int:
    plugin_root = Path(__file__).resolve().parents[1]
    fixture = plugin_root / "tests" / "fixtures" / "trigger-cases.json"
    try:
        payload = strict_json_loads(fixture.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, StrictJSONError) as exc:
        print(f"unable to read trigger fixture: {exc}", file=sys.stderr)
        return 2
    errors: list[str] = []
    cases = payload.get("skills") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        print("trigger fixture requires a skills array", file=sys.stderr)
        return 1
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            errors.append("trigger case must be an object")
            continue
        name = case.get("name")
        if not isinstance(name, str) or name in seen:
            errors.append(f"invalid or duplicate skill name: {name!r}")
            continue
        seen.add(name)
        if not (plugin_root / "skills" / name / "SKILL.md").is_file():
            errors.append(f"missing skill entrypoint: {name}")
        for key in ("should_trigger", "should_not_trigger"):
            values = case.get(key)
            if not isinstance(values, list) or len(values) < 2 or not all(
                isinstance(item, str) and item.strip() for item in values
            ):
                errors.append(f"{name}.{key} needs at least two nonempty strings")
    actual = {path.parent.name for path in (plugin_root / "skills").glob("*/SKILL.md")}
    if seen != actual:
        errors.append(f"fixture skills differ from entrypoints: fixture={sorted(seen)} actual={sorted(actual)}")
    result = {
        "schema": "career.trigger_contract_report.v1",
        "valid": not errors,
        "skills": len(seen),
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


def add_validation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("target")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument("--as-of")
    parser.set_defaults(func=cmd_validate)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a record file or workspace")
    add_validation_args(validate)
    validate_record = subparsers.add_parser("validate-record", help="validate one record file")
    add_validation_args(validate_record)
    validate_workspace = subparsers.add_parser("validate-workspace", help="validate a workspace")
    add_validation_args(validate_workspace)

    init = subparsers.add_parser("init-workspace", help="create missing workspace files")
    init.add_argument("root")
    init.add_argument("--timestamp")
    init.add_argument("--subject-id")
    init.set_defaults(func=cmd_init_workspace)

    append = subparsers.add_parser("verify-append", help="prove old ledgers are a semantic prefix")
    append.add_argument("--base", required=True)
    append.add_argument("--candidate", required=True)
    append.add_argument("--json", action="store_true")
    append.set_defaults(func=cmd_verify_append)

    for name in ("approval-hash", "effect-hash"):
        approval = subparsers.add_parser(name, help="calculate and verify an effect approval hash")
        approval.add_argument("plan")
        approval.add_argument("--as-of")
        approval.add_argument("--json", action="store_true")
        approval.set_defaults(func=cmd_approval_hash)

    project = subparsers.add_parser("project", help="project current facts and pipeline state")
    project.add_argument("root")
    project.add_argument("--opportunity")
    project.add_argument("--as-of")
    project.add_argument("--strict-warnings", action="store_true")
    project.add_argument("--json", action="store_true")
    project.set_defaults(func=cmd_project)

    ops = subparsers.add_parser("ops-brief", help="derive a deterministic current-state and next-action brief")
    ops.add_argument("root")
    ops.add_argument("--as-of", required=True)
    ops.add_argument("--strict-warnings", action="store_true")
    ops.add_argument("--json", action="store_true")
    ops.set_defaults(func=cmd_ops_brief)

    append_event = subparsers.add_parser("append-event", help="atomically append a verified pipeline event")
    append_event.add_argument("--workspace", required=True)
    append_event.add_argument("--event", required=True)
    append_event.add_argument("--expected-tail-id", required=True)
    append_event.add_argument("--json", action="store_true")
    append_event.set_defaults(func=cmd_append_event)

    score = subparsers.add_parser("score-fit", help="calculate a transparent fit prioritization")
    score.add_argument("analysis")
    score.set_defaults(func=cmd_score_fit)

    claims = subparsers.add_parser("validate-claims", help="verify artifact claims against active facts")
    claims.add_argument("--facts", required=True)
    claims.add_argument("--evidence", required=True)
    claims.add_argument("--manifest", required=True)
    claims.add_argument("--json", action="store_true")
    claims.add_argument("--strict-warnings", action="store_true")
    claims.set_defaults(func=cmd_validate_claims)

    dedupe = subparsers.add_parser("dedupe-opportunities", help="report potential duplicate opportunities")
    dedupe.add_argument("opportunities")
    dedupe.set_defaults(func=cmd_dedupe_opportunities)

    triggers = subparsers.add_parser("check-triggers", help="validate trigger-contract fixtures")
    triggers.set_defaults(func=cmd_check_triggers)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
