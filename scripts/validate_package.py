#!/usr/bin/env python3
"""Validate the standalone Career Skills package without network access."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "scripts" / "career_core.py"
SPEC = importlib.util.spec_from_file_location("career_core_validation", CORE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load career_core.py")
CORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)

ABSOLUTE_WINDOWS = re.compile(
    "(?:[a-z]" + ":" + re.escape("\\") + "|c:/" + "users/|e:/" + "projects/)",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def read_json(path: Path) -> dict:
    value = CORE.strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root JSON value must be an object")
    return value


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    try:
        block = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc
    result: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        key, separator, raw = line.partition(":")
        if not separator:
            raise ValueError(f"invalid frontmatter line: {line}")
        result[key.strip()] = raw.strip().strip('"')
    return result


def tracked_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            check=True,
            stdout=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return [path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]
    tracked = [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]
    if tracked:
        return tracked
    return [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    ]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    manifests = []
    for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        path = ROOT / relative
        try:
            manifests.append(read_json(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{relative}: {exc}")
    if len(manifests) == 2:
        shared = ("name", "version", "description", "author", "homepage", "repository", "license", "keywords")
        for key in shared:
            if manifests[0].get(key) != manifests[1].get(key):
                errors.append(f"manifest parity: {key} differs")
        if manifests[0].get("name") != "career":
            errors.append("manifest name must remain the stable plugin id 'career'")
        if manifests[0].get("repository") != "https://github.com/Xopoko/career-skills":
            errors.append("manifest repository must point to the standalone source")

    cursor_manifest = None
    try:
        cursor_manifest = read_json(ROOT / ".cursor-plugin" / "plugin.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f".cursor-plugin/plugin.json: {exc}")
    if cursor_manifest is not None:
        if cursor_manifest.get("name") != "career":
            errors.append("Cursor manifest name must remain the stable plugin id 'career'")
        if cursor_manifest.get("repository") != "https://github.com/Xopoko/career-skills":
            errors.append("Cursor manifest repository must point to the standalone source")
        if manifests and cursor_manifest.get("version") != manifests[0].get("version"):
            errors.append("Cursor manifest version differs from the shared plugin version")
        if "skills" in cursor_manifest:
            errors.append("Cursor manifest must use default skills/ discovery; wildcard paths are not supported")
        logo = cursor_manifest.get("logo")
        if not isinstance(logo, str) or not (ROOT / logo).is_file():
            errors.append("Cursor manifest logo must resolve to a repository file")

    marketplace = None
    try:
        marketplace = read_json(ROOT / ".claude-plugin" / "marketplace.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f".claude-plugin/marketplace.json: {exc}")
    if marketplace is not None:
        if marketplace.get("name") != "career-skills":
            errors.append("Claude marketplace name must be 'career-skills'")
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list) or len(plugins) != 1 or not isinstance(plugins[0], dict):
            errors.append("Claude marketplace must declare exactly one plugin")
        else:
            entry = plugins[0]
            if entry.get("name") != "career" or entry.get("source") != "./":
                errors.append("Claude marketplace plugin must bind career to the repository root")
            if manifests:
                for key in ("version", "description", "repository", "license"):
                    if entry.get(key) != manifests[0].get(key):
                        errors.append(f"Claude marketplace plugin {key} differs from the shared manifest")

    skill_paths = sorted((ROOT / "skills").glob("*/SKILL.md"))
    skill_names: set[str] = set()
    for path in skill_paths:
        relative = path.relative_to(ROOT).as_posix()
        try:
            metadata = frontmatter(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        name = metadata.get("name")
        description = metadata.get("description")
        if name != path.parent.name:
            errors.append(f"{relative}: frontmatter name must match directory")
        if not description or len(description) > 1024:
            errors.append(f"{relative}: description must contain 1-1024 characters")
        if name in skill_names:
            errors.append(f"duplicate skill name: {name}")
        if isinstance(name, str):
            skill_names.add(name)

    trigger_result = subprocess.run(
        [sys.executable, str(CORE_PATH), "check-triggers"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if trigger_result.returncode != 0:
        errors.append(f"trigger fixture validation failed: {trigger_result.stdout or trigger_result.stderr}")

    template_count = 0
    for path in sorted((ROOT / "templates").glob("*.json")):
        try:
            value = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT).as_posix()}: {exc}")
            continue
        if value.get("schema") not in CORE.CORE_SCHEMAS:
            continue
        template_count += 1
        record = CORE.LoadedRecord(value, path.relative_to(ROOT).as_posix(), 1)
        diagnostics = []
        CORE.validate_record_structure(record, diagnostics)
        errors.extend(
            f"{item.file}:{item.json_path}: {item.code}: {item.message}"
            for item in diagnostics
            if item.severity == "error"
        )
        warnings.extend(
            f"{item.file}:{item.json_path}: {item.code}: {item.message}"
            for item in diagnostics
            if item.severity == "warning"
        )

    files = tracked_files()
    for relative in files:
        if "__pycache__" in relative.parts or relative.suffix == ".pyc":
            errors.append(f"generated Python artifact is tracked: {relative.as_posix()}")
        path = ROOT / relative
        if path.suffix.lower() not in {".md", ".json", ".jsonl", ".yaml", ".yml", ".py"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if relative.as_posix() not in {"scripts/validate_package.py", "tests/test_career_core.py"} and ABSOLUTE_WINDOWS.search(text):
            errors.append(f"private or machine-specific absolute path in {relative.as_posix()}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret material in {relative.as_posix()}")

    result = {
        "schema": "career.package_validation.v1",
        "valid": not errors,
        "counts": {
            "skills": len(skill_names),
            "core_templates": template_count,
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "errors": sorted(errors),
        "warnings": sorted(warnings),
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
