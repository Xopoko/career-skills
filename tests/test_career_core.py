import contextlib
import copy
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PLUGIN_ROOT / "scripts" / "career_core.py"
SPEC = importlib.util.spec_from_file_location("career_core", CORE_PATH)
assert SPEC and SPEC.loader
core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
SPEC.loader.exec_module(core)


def read_template(name):
    return json.loads(
        (PLUGIN_ROOT / "templates" / name).read_text(encoding="utf-8")
    )


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(value, sort_keys=True) + "\n" for value in values),
        encoding="utf-8",
    )


class CareerCoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "career-data"
        self.make_good_workspace(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def make_good_workspace(self, root):
        profile = read_template("profile.example.json")
        policy = read_template("search-policy.example.json")
        evidence = read_template("evidence-receipt.example.json")
        fact = read_template("fact.example.json")
        opportunity = read_template("opportunity.example.json")
        event = read_template("pipeline-event.example.json")
        plan = read_template("effect-plan.example.json")
        artifact = read_template("artifact-receipt.example.json")
        campaign = read_template("application-campaign.example.json")
        action = read_template("action.example.json")
        write_json(root / "profile.json", profile)
        write_json(root / "search-policy.json", policy)
        write_jsonl(root / "evidence.jsonl", [evidence])
        write_jsonl(root / "facts.jsonl", [fact])
        write_jsonl(root / "opportunities.jsonl", [opportunity])
        write_jsonl(root / "pipeline-events.jsonl", [event])
        write_jsonl(root / "actions.jsonl", [action])
        write_json(root / "plans" / "effects" / "example.json", plan)
        write_jsonl(root / "artifacts" / "index.jsonl", [artifact])
        write_json(root / "plans" / "campaigns" / "example.json", campaign)

    def report(self, root=None, strict=False, as_of=None):
        records, diagnostics = core.load_workspace(root or self.root, as_of)
        return core.validation_report(diagnostics, records, strict)

    def approve_plan(self, *, expires_at="2026-08-14T10:04:00Z", approved_at="2026-08-13T10:04:00Z"):
        path = self.root / "plans" / "effects" / "example.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["expires_at"] = expires_at
        plan["approval"] = {
            "state": "approved",
            "approved_by": "user",
            "approved_at": approved_at,
        }
        plan["approval_hash"] = core.canonical_sha256(core.approval_basis(plan))
        write_json(path, plan)
        return plan

    def effect_event(self, event_id, previous_event_id, recorded_at, outcome="succeeded"):
        plan_path = self.root / "plans" / "effects" / "example.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if plan.get("approval", {}).get("state") != "approved":
            plan = self.approve_plan()
        event = read_template("pipeline-event.example.json")
        event.update(
            {
                "id": event_id,
                "previous_event_id": previous_event_id,
                "recorded_at": recorded_at,
                "effective_at": recorded_at,
                "type": "effect_executed",
                "status_before": "discovered",
                "status_after": "discovered",
                "effect_result": {
                    "plan_id": "plan-88888888-8888-4888-8888-888888888888",
                    "plan_revision_id": "plan-revision-99999999-9999-4999-8999-999999999999",
                    "approval_hash": plan["approval_hash"],
                    "outcome": outcome,
                    "provider_receipt": "evidence-22222222-2222-4222-8222-222222222222",
                },
            }
        )
        return event

    def reconciliation_event(
        self,
        event_id,
        ambiguous,
        recorded_at,
        resolution="not_occurred",
    ):
        target_result = ambiguous["effect_result"]
        event = read_template("pipeline-event.example.json")
        event.update(
            {
                "id": event_id,
                "opportunity_id": ambiguous["opportunity_id"],
                "previous_event_id": ambiguous["id"],
                "recorded_at": recorded_at,
                "effective_at": recorded_at,
                "type": "effect_reconciled",
                "status_before": ambiguous["status_after"],
                "status_after": ambiguous["status_after"],
                "effect_reconciliation": {
                    "plan_id": target_result["plan_id"],
                    "plan_revision_id": target_result["plan_revision_id"],
                    "approval_hash": target_result["approval_hash"],
                    "ambiguous_event_id": ambiguous["id"],
                    "resolution": resolution,
                },
            }
        )
        return event

    def test_good_workspace_is_cross_linked_and_valid(self):
        report = self.report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(10, report["counts"]["records"])
        self.assertEqual(0, report["counts"]["errors"])

    def test_trigger_contract_covers_every_skill(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = core.cmd_check_triggers(Namespace())
        payload = json.loads(output.getvalue())
        self.assertEqual(0, result)
        self.assertTrue(payload["valid"])
        self.assertEqual(20, payload["skills"])

    def test_approval_hash_is_stable_across_key_order(self):
        plan = read_template("effect-plan.example.json")
        reversed_plan = dict(reversed(list(plan.items())))
        self.assertEqual(
            core.canonical_sha256(core.approval_basis(plan)),
            core.canonical_sha256(core.approval_basis(reversed_plan)),
        )

    def test_one_byte_effect_change_invalidates_approval_hash(self):
        path = self.root / "plans" / "effects" / "example.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["effect"]["payload"]["body"] += "!"
        write_json(path, plan)
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("plan.approval_hash_mismatch", codes)

    def test_approved_plan_needs_actor_and_time(self):
        path = self.root / "plans" / "effects" / "example.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["approval"] = {"state": "approved"}
        write_json(path, plan)
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("field.string_required", codes)
        self.assertIn("field.rfc3339_required", codes)

    def test_future_approval_is_not_executable(self):
        plan = self.approve_plan(approved_at="2026-08-13T12:00:00Z")
        executable, reason = core.plan_executable(
            plan, core.parse_time("2026-08-13T11:00:00Z")
        )
        self.assertFalse(executable)
        self.assertIn("not yet approved", reason)

    def test_invalid_plan_timestamp_order_fails(self):
        path = self.root / "plans" / "effects" / "example.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["expires_at"] = plan["created_at"]
        plan["approval_hash"] = core.canonical_sha256(core.approval_basis(plan))
        write_json(path, plan)
        self.assertIn("plan.invalid_expiry", {item["code"] for item in self.report()["errors"]})

    def test_pending_plan_is_valid_but_not_executable(self):
        plan = read_template("effect-plan.example.json")
        executable, reason = core.plan_executable(plan, core.parse_time("2026-08-13T11:00:00Z"))
        self.assertFalse(executable)
        self.assertIn("not approved", reason)

    def test_duplicate_json_key_is_rejected(self):
        path = self.root / "duplicate.json"
        path.write_text('{"schema":"career.fact.v1","schema":"career.fact.v1"}\n')
        _, diagnostics = core.read_records(path)
        self.assertIn("json.parse", {item.code for item in diagnostics})

    def test_non_finite_json_number_is_rejected(self):
        path = self.root / "nan.json"
        path.write_text('{"schema":"career.fact.v1","value":NaN}\n')
        _, diagnostics = core.read_records(path)
        self.assertIn("json.parse", {item.code for item in diagnostics})

    def test_float_and_unsafe_integer_are_rejected(self):
        fact = read_template("fact.example.json")
        fact["value"] = {"ratio": 0.5, "count": 2**60}
        record = core.LoadedRecord(fact, "memory.json", 1)
        diagnostics = []
        core.validate_record_structure(record, diagnostics)
        codes = {item.code for item in diagnostics}
        self.assertIn("json.float_forbidden", codes)
        self.assertIn("json.unsafe_integer", codes)

    def test_absolute_windows_evidence_path_is_rejected(self):
        evidence = read_template("evidence-receipt.example.json")
        evidence["source"] = {
            "kind": "file",
            "locator": "C:\\private\\resume.pdf",
            "captured_at": "2026-08-13T09:58:00Z",
        }
        evidence["integrity"]["sha256"] = "0" * 64
        record = core.LoadedRecord(evidence, "memory.json", 1)
        diagnostics = []
        core.validate_record_structure(record, diagnostics)
        self.assertIn("evidence.unsafe_locator", {item.code for item in diagnostics})

    def test_missing_evidence_reference_fails(self):
        (self.root / "evidence.jsonl").write_text("", encoding="utf-8")
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("reference.missing_evidence", codes)

    def test_undeclared_active_fact_conflict_fails(self):
        first = read_template("fact.example.json")
        second = copy.deepcopy(first)
        second["fact_id"] = "fact-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        second["revision_id"] = "fact-revision-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        second["value"]["result"] = "Different result"
        write_jsonl(self.root / "facts.jsonl", [first, second])
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("fact.undeclared_conflict", codes)

    def test_explicit_active_fact_conflict_projects_disputed(self):
        first = read_template("fact.example.json")
        second = copy.deepcopy(first)
        second["fact_id"] = "fact-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        second["revision_id"] = "fact-revision-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        second["value"]["result"] = "Different result"
        second["contradicts_fact_ids"] = [first["fact_id"]]
        write_jsonl(self.root / "facts.jsonl", [first, second])
        report = self.report()
        self.assertTrue(report["valid"], report)
        self.assertIn("fact.disputed", {item["code"] for item in report["warnings"]})
        records, _ = core.load_workspace(self.root)
        projection = core.current_projection(records)
        self.assertEqual("disputed", projection["facts"][0]["state"])

    def test_missing_contradicted_fact_fails(self):
        fact = read_template("fact.example.json")
        fact["contradicts_fact_ids"] = ["fact-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
        write_jsonl(self.root / "facts.jsonl", [fact])
        self.assertIn(
            "fact.missing_contradiction_target",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_strict_warnings_promote_unknown_normalization(self):
        opportunity = read_template("opportunity.example.json")
        opportunity["normalized"]["seniority"] = "unknown"
        opportunity["normalization_warnings"] = []
        write_jsonl(self.root / "opportunities.jsonl", [opportunity])
        self.assertTrue(self.report(strict=False)["valid"])
        self.assertFalse(self.report(strict=True)["valid"])

    def test_closed_status_requires_outcome(self):
        event = read_template("pipeline-event.example.json")
        event["status_after"] = "closed"
        event["outcome"] = None
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("event.closed_without_outcome", codes)

    def test_open_status_forbids_terminal_outcome(self):
        event = read_template("pipeline-event.example.json")
        event["outcome"] = {"kind": "rejected"}
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("event.open_with_outcome", codes)

    def test_proposed_interview_is_not_scheduled(self):
        event = read_template("pipeline-event.example.json")
        event["type"] = "interview_proposed"
        event["status_after"] = "interviewing"
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("event.proposal_is_not_scheduled", codes)

    def test_confirmed_recruiter_chat_does_not_become_interview(self):
        first = read_template("pipeline-event.example.json")
        second = copy.deepcopy(first)
        second.update(
            {
                "id": "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "previous_event_id": first["id"],
                "status_before": "discovered",
                "status_after": "considering",
                "type": "recruiter_chat_scheduled",
                "interaction": {
                    "kind": "recruiter_chat",
                    "schedule_state": "scheduled",
                    "calendar_state": "confirmed",
                },
            }
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, second])
        report = self.report()
        self.assertTrue(report["valid"], report)
        records, _ = core.load_workspace(self.root)
        projected = core.current_projection(records)
        self.assertEqual("considering", projected["opportunities"][0]["status"])

    def test_recruiter_contact_cannot_enter_interviewing(self):
        event = read_template("pipeline-event.example.json")
        event["type"] = "recruiter_contact"
        event["status_after"] = "interviewing"
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        self.assertIn("event.proposal_is_not_scheduled", {item["code"] for item in self.report()["errors"]})

    def test_correction_requires_evidence(self):
        first = read_template("pipeline-event.example.json")
        second = copy.deepcopy(first)
        second.update(
            {
                "id": "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "previous_event_id": first["id"],
                "status_before": "discovered",
                "status_after": "discovered",
                "type": "correction",
                "correction_of_event_id": first["id"],
                "evidence_ids": [],
            }
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, second])
        self.assertIn("event.correction_evidence_required", {item["code"] for item in self.report()["errors"]})

    def test_effect_result_is_required_and_exclusive(self):
        event = read_template("pipeline-event.example.json")
        event["type"] = "effect_executed"
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        self.assertIn("event.effect_result_required", {item["code"] for item in self.report()["errors"]})
        event["type"] = "note"
        event["effect_result"] = {
            "plan_id": "plan-88888888-8888-4888-8888-888888888888",
            "plan_revision_id": "plan-revision-99999999-9999-4999-8999-999999999999",
            "approval_hash": "0" * 64,
            "outcome": "succeeded",
        }
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        self.assertIn("event.effect_result_misattached", {item["code"] for item in self.report()["errors"]})

    def test_provider_status_is_validated(self):
        event = read_template("pipeline-event.example.json")
        event["provider_status"] = {
            "provider_id": "NOT VALID",
            "raw": "new",
            "mapped_status": "unknown",
            "mapping_version": "v1",
        }
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        report = self.report()
        self.assertIn("provider.id", {item["code"] for item in report["errors"]})
        self.assertIn("event.provider_status_unmapped", {item["code"] for item in report["warnings"]})

    def test_event_tail_and_status_before_are_checked(self):
        first = read_template("pipeline-event.example.json")
        second = copy.deepcopy(first)
        second["id"] = "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        second["previous_event_id"] = None
        second["status_before"] = None
        second["status_after"] = "considering"
        second["type"] = "review_started"
        write_jsonl(self.root / "pipeline-events.jsonl", [first, second])
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("event.tail_mismatch", codes)
        self.assertIn("event.status_before_mismatch", codes)

    def test_append_event_checks_tail_and_writes_atomically(self):
        first = read_template("pipeline-event.example.json")
        second = copy.deepcopy(first)
        second["id"] = "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        second["previous_event_id"] = first["id"]
        second["status_before"] = "discovered"
        second["status_after"] = "considering"
        second["type"] = "review_started"
        incoming = Path(self.temp.name) / "event.json"
        write_json(incoming, second)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = core.cmd_append_event(
                Namespace(
                    workspace=str(self.root),
                    event=str(incoming),
                    expected_tail_id=first["id"],
                    json=True,
                )
            )
        self.assertEqual(0, result, output.getvalue())
        records, diagnostics = core.read_records(self.root / "pipeline-events.jsonl")
        self.assertFalse([item for item in diagnostics if item.severity == "error"])
        self.assertEqual(2, len(records))

    def test_concurrent_append_is_compare_and_swap(self):
        first = read_template("pipeline-event.example.json")
        paths = []
        for suffix, event_id in (
            ("a", "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            ("b", "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ):
            event = copy.deepcopy(first)
            event.update(
                {
                    "id": event_id,
                    "previous_event_id": first["id"],
                    "status_before": "discovered",
                    "status_after": "considering",
                    "type": "review_started",
                }
            )
            path = Path(self.temp.name) / f"event-{suffix}.json"
            write_json(path, event)
            paths.append(path)
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    str(CORE_PATH),
                    "append-event",
                    "--workspace",
                    str(self.root),
                    "--event",
                    str(path),
                    "--expected-tail-id",
                    first["id"],
                    "--json",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for path in paths
        ]
        results = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
        self.assertEqual([0, 1], sorted(result[2] for result in results), results)
        records, diagnostics = core.read_records(self.root / "pipeline-events.jsonl")
        self.assertFalse([item for item in diagnostics if item.severity == "error"])
        self.assertEqual(2, len(records))

    def test_expired_plan_cannot_record_execution(self):
        first = read_template("pipeline-event.example.json")
        self.approve_plan(expires_at="2026-08-13T10:05:00Z")
        effect = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:06:00Z",
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, effect])
        self.assertIn("event.plan_not_approved", {item["code"] for item in self.report()["errors"]})

    def test_effect_authorization_uses_effective_at_for_occurrence(self):
        first = read_template("pipeline-event.example.json")
        self.approve_plan(expires_at="2026-08-13T10:05:00Z")
        effect = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:06:00Z",
        )
        effect["effective_at"] = "2026-08-13T10:04:30Z"
        write_jsonl(self.root / "pipeline-events.jsonl", [first, effect])
        report = self.report()
        self.assertTrue(report["valid"], report)

    def test_effect_before_approval_is_rejected_even_when_recorded_later(self):
        first = read_template("pipeline-event.example.json")
        self.approve_plan(approved_at="2026-08-13T10:04:00Z")
        effect = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
        )
        effect["effective_at"] = "2026-08-13T10:03:30Z"
        write_jsonl(self.root / "pipeline-events.jsonl", [first, effect])
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("event.plan_not_approved", codes)

    def test_effect_plan_must_match_event_opportunity(self):
        first = read_template("pipeline-event.example.json")
        plan = self.approve_plan()
        plan["opportunity_id"] = "opportunity-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        plan["approval_hash"] = core.canonical_sha256(core.approval_basis(plan))
        write_json(self.root / "plans" / "effects" / "example.json", plan)
        effect = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, effect])
        self.assertIn(
            "event.plan_opportunity_mismatch",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_succeeded_effect_requires_provider_receipt(self):
        first = read_template("pipeline-event.example.json")
        effect = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
        )
        del effect["effect_result"]["provider_receipt"]
        write_jsonl(self.root / "pipeline-events.jsonl", [first, effect])
        self.assertIn(
            "event.succeeded_receipt_required",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_succeeded_effect_provider_receipt_must_resolve(self):
        first = read_template("pipeline-event.example.json")
        effect = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
        )
        effect["effect_result"]["provider_receipt"] = (
            "evidence-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, effect])
        self.assertIn(
            "event.succeeded_receipt_unresolved",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_revoked_plan_revision_cannot_record_execution(self):
        first = read_template("pipeline-event.example.json")
        approved = self.approve_plan()
        revoked = copy.deepcopy(approved)
        revoked["revision_id"] = "plan-revision-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        revoked["supersedes_revision_id"] = approved["revision_id"]
        revoked["recorded_at"] = "2026-08-13T10:05:00Z"
        revoked["approval"] = {"state": "revoked"}
        effect = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:06:00Z",
        )
        effect["effect_result"]["approval_hash"] = approved["approval_hash"]
        write_jsonl(self.root / "plans" / "effects" / "revisions.jsonl", [approved, revoked])
        (self.root / "plans" / "effects" / "example.json").unlink()
        write_jsonl(self.root / "pipeline-events.jsonl", [first, effect])
        self.assertIn("event.plan_revision_not_current", {item["code"] for item in self.report()["errors"]})

    def test_ambiguous_effect_requires_reconciliation_before_retry(self):
        first = read_template("pipeline-event.example.json")
        self.approve_plan()
        ambiguous = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
            "ambiguous",
        )
        retry = self.effect_event(
            "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ambiguous["id"],
            "2026-08-13T10:06:00Z",
            "succeeded",
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, ambiguous, retry])
        self.assertIn("event.ambiguous_retry", {item["code"] for item in self.report()["errors"]})

    def test_exact_reconciliation_allows_retry_after_not_occurred(self):
        first = read_template("pipeline-event.example.json")
        self.approve_plan()
        ambiguous = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
            "ambiguous",
        )
        reconciliation = self.reconciliation_event(
            "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ambiguous,
            "2026-08-13T10:06:00Z",
        )
        retry = self.effect_event(
            "event-cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            reconciliation["id"],
            "2026-08-13T10:07:00Z",
        )
        write_jsonl(
            self.root / "pipeline-events.jsonl",
            [first, ambiguous, reconciliation, retry],
        )
        report = self.report()
        self.assertTrue(report["valid"], report)

    def test_reconciliation_must_be_terminal(self):
        first = read_template("pipeline-event.example.json")
        ambiguous = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
            "ambiguous",
        )
        reconciliation = self.reconciliation_event(
            "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ambiguous,
            "2026-08-13T10:06:00Z",
            "unknown",
        )
        write_jsonl(
            self.root / "pipeline-events.jsonl", [first, ambiguous, reconciliation]
        )
        errors = self.report()["errors"]
        self.assertTrue(
            any(
                item["code"] == "field.enum"
                and item["json_path"] == "$.effect_reconciliation.resolution"
                for item in errors
            ),
            errors,
        )

    def test_duplicate_and_contradictory_reconciliations_are_rejected(self):
        for second_resolution, expected_code in (
            ("not_occurred", "event.duplicate_reconciliation"),
            ("occurred", "event.contradictory_reconciliation"),
        ):
            with self.subTest(second_resolution=second_resolution):
                self.make_good_workspace(self.root)
                first = read_template("pipeline-event.example.json")
                ambiguous = self.effect_event(
                    "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    first["id"],
                    "2026-08-13T10:05:00Z",
                    "ambiguous",
                )
                first_reconciliation = self.reconciliation_event(
                    "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    ambiguous,
                    "2026-08-13T10:06:00Z",
                )
                second_reconciliation = self.reconciliation_event(
                    "event-cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                    ambiguous,
                    "2026-08-13T10:07:00Z",
                    second_resolution,
                )
                second_reconciliation["previous_event_id"] = first_reconciliation["id"]
                write_jsonl(
                    self.root / "pipeline-events.jsonl",
                    [first, ambiguous, first_reconciliation, second_reconciliation],
                )
                self.assertIn(
                    expected_code,
                    {item["code"] for item in self.report()["errors"]},
                )

    def test_reconciliation_binds_exact_target_execution(self):
        cases = (
            (
                "plan_id",
                "plan-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "event.reconciliation_plan_mismatch",
            ),
            (
                "plan_revision_id",
                "plan-revision-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "event.reconciliation_revision_mismatch",
            ),
            ("approval_hash", "0" * 64, "event.reconciliation_hash_mismatch"),
        )
        for field, wrong_value, expected_code in cases:
            with self.subTest(field=field):
                self.make_good_workspace(self.root)
                first = read_template("pipeline-event.example.json")
                ambiguous = self.effect_event(
                    "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    first["id"],
                    "2026-08-13T10:05:00Z",
                    "ambiguous",
                )
                reconciliation = self.reconciliation_event(
                    "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    ambiguous,
                    "2026-08-13T10:06:00Z",
                )
                reconciliation["effect_reconciliation"][field] = wrong_value
                write_jsonl(
                    self.root / "pipeline-events.jsonl",
                    [first, ambiguous, reconciliation],
                )
                self.assertIn(
                    expected_code,
                    {item["code"] for item in self.report()["errors"]},
                )

    def test_reconciliation_binds_target_opportunity(self):
        first = read_template("pipeline-event.example.json")
        ambiguous = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
            "ambiguous",
        )
        reconciliation = self.reconciliation_event(
            "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ambiguous,
            "2026-08-13T10:06:00Z",
        )
        reconciliation["opportunity_id"] = (
            "opportunity-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        )
        write_jsonl(
            self.root / "pipeline-events.jsonl", [first, ambiguous, reconciliation]
        )
        self.assertIn(
            "event.reconciliation_opportunity_mismatch",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_reconciliation_target_must_resolve(self):
        first = read_template("pipeline-event.example.json")
        ambiguous = self.effect_event(
            "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            first["id"],
            "2026-08-13T10:05:00Z",
            "ambiguous",
        )
        reconciliation = self.reconciliation_event(
            "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ambiguous,
            "2026-08-13T10:06:00Z",
        )
        reconciliation["effect_reconciliation"]["ambiguous_event_id"] = (
            "event-cccccccc-cccc-4ccc-8ccc-cccccccccccc"
        )
        write_jsonl(
            self.root / "pipeline-events.jsonl", [first, ambiguous, reconciliation]
        )
        self.assertIn(
            "event.missing_ambiguous_event",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_application_submitted_requires_nonempty_evidence(self):
        first = read_template("pipeline-event.example.json")
        applied = copy.deepcopy(first)
        applied.update(
            {
                "id": "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "previous_event_id": first["id"],
                "status_before": "discovered",
                "status_after": "applied",
                "type": "application_submitted",
                "evidence_ids": [],
            }
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, applied])
        self.assertIn(
            "event.application_evidence_required",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_application_submitted_evidence_must_resolve(self):
        first = read_template("pipeline-event.example.json")
        applied = copy.deepcopy(first)
        applied.update(
            {
                "id": "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "previous_event_id": first["id"],
                "status_before": "discovered",
                "status_after": "applied",
                "type": "application_submitted",
                "evidence_ids": [
                    "evidence-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
                ],
            }
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, applied])
        self.assertIn(
            "event.application_evidence_unresolved",
            {item["code"] for item in self.report()["errors"]},
        )

    def test_generic_submission_evidence_is_not_provider_acknowledgement(self):
        evidence = read_template("evidence-receipt.example.json")
        evidence["source"]["kind"] = "email"
        write_jsonl(self.root / "evidence.jsonl", [evidence])
        first = read_template("pipeline-event.example.json")
        applied = copy.deepcopy(first)
        applied.update(
            {
                "id": "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "previous_event_id": first["id"],
                "status_before": "discovered",
                "status_after": "applied",
                "type": "application_submitted",
            }
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, applied])
        report = self.report()
        self.assertTrue(report["valid"], report)
        records, _ = core.load_workspace(self.root)
        projection = core.current_projection(records)
        self.assertEqual(
            "documented_without_provider_acknowledgement",
            projection["opportunities"][0]["submission_verification"]["basis"],
        )

    def test_progressed_application_remains_in_submitted_milestone(self):
        first = read_template("pipeline-event.example.json")
        applied = copy.deepcopy(first)
        applied.update(
            {
                "id": "event-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "previous_event_id": first["id"],
                "status_before": "discovered",
                "status_after": "applied",
                "type": "application_submitted",
            }
        )
        screening = copy.deepcopy(first)
        screening.update(
            {
                "id": "event-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "previous_event_id": applied["id"],
                "status_before": "applied",
                "status_after": "screening",
                "type": "recruiter_contact",
            }
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [first, applied, screening])
        report = self.report()
        self.assertTrue(report["valid"], report)
        records, _ = core.load_workspace(self.root)
        projection = core.current_projection(records)
        self.assertEqual("screening", projection["opportunities"][0]["status"])
        self.assertEqual(1, projection["metrics"]["ever_reached"]["application_submitted"])
        self.assertEqual("user_reported", projection["opportunities"][0]["submission_verification"]["basis"])

    def test_workspace_requires_profile_policy_and_artifact_index(self):
        (self.root / "profile.json").unlink()
        (self.root / "artifacts" / "index.jsonl").unlink()
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("workspace.missing_record", codes)
        self.assertIn("workspace.missing_ledger", codes)

    def test_campaign_allows_reserve_beyond_target_quota(self):
        campaign = read_template("application-campaign.example.json")
        reserve = copy.deepcopy(campaign["items"][0])
        reserve.update(
            {
                "item_id": "campaign-item-ffffffff-ffff-4fff-8fff-ffffffffffff",
                "slot_id": "reserve-01",
                "cohort_role": "reserve",
                "opportunity_id": "opportunity-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            }
        )
        campaign["items"].append(reserve)
        campaign["reserve_count"] = 1
        campaign["counts"]["queued"] = 2
        diagnostics = []
        core.validate_record_structure(core.LoadedRecord(campaign, "memory.json", 1), diagnostics)
        self.assertFalse([item for item in diagnostics if item.severity == "error"], diagnostics)

    def test_campaign_rejects_duplicate_item_and_slot_ids(self):
        campaign = read_template("application-campaign.example.json")
        campaign["items"].append(copy.deepcopy(campaign["items"][0]))
        campaign["roster_count"] = 2
        campaign["counts"]["queued"] = 2
        diagnostics = []
        core.validate_record_structure(core.LoadedRecord(campaign, "memory.json", 1), diagnostics)
        codes = {item.code for item in diagnostics if item.severity == "error"}
        self.assertIn("campaign.duplicate_item", codes)
        self.assertIn("campaign.duplicate_slot", codes)

    def test_completed_campaign_requires_acknowledged_effect_receipt(self):
        plan_path = self.root / "plans" / "effects" / "example.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        event = read_template("pipeline-event.example.json")
        event.update(
            {
                "recorded_at": "2026-08-13T10:05:00Z",
                "effective_at": "2026-08-13T10:05:00Z",
                "type": "effect_executed",
                "effect_result": {
                    "plan_id": plan["plan_id"],
                    "plan_revision_id": plan["revision_id"],
                    "approval_hash": plan["approval_hash"],
                    "outcome": "succeeded",
                    "provider_receipt": "evidence-22222222-2222-4222-8222-222222222222",
                },
            }
        )
        write_jsonl(self.root / "pipeline-events.jsonl", [event])
        campaign_path = self.root / "plans" / "campaigns" / "example.json"
        campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
        item = campaign["items"][0]
        item.update(
            {
                "plan_id": plan["plan_id"],
                "plan_revision_id": plan["revision_id"],
                "approval_hash": plan["approval_hash"],
                "state": "succeeded",
                "attempted_at": event["effective_at"],
                "effect_event_id": event["id"],
            }
        )
        campaign["state"] = "completed"
        campaign["counts"]["queued"] = 0
        campaign["counts"]["attempted"] = 1
        campaign["counts"]["succeeded"] = 1
        write_json(campaign_path, campaign)
        codes = {item["code"] for item in self.report()["errors"]}
        self.assertIn("event.plan_not_approved", codes)
        self.assertIn("campaign.plan_action", codes)

    def test_as_of_projection_ignores_future_and_tolerates_expired_history(self):
        self.approve_plan()
        before_plan = self.report(as_of=core.parse_time("2026-08-13T10:03:00Z"))
        self.assertTrue(before_plan["valid"], before_plan)
        after_expiry = self.report(as_of=core.parse_time("2026-08-15T10:04:00Z"))
        self.assertTrue(after_expiry["valid"], after_expiry)

    def test_profile_and_search_policy_subjects_must_match(self):
        policy_path = self.root / "search-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy["subject_id"] = "subject-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        write_json(policy_path, policy)
        self.assertIn("workspace.subject_mismatch", {item["code"] for item in self.report()["errors"]})

    def test_partial_init_reuses_existing_subject(self):
        partial = Path(self.temp.name) / "partial-career-data"
        write_json(partial / "profile.json", read_template("profile.example.json"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = core.cmd_init_workspace(
                Namespace(
                    root=str(partial),
                    timestamp="2026-08-13T10:00:00Z",
                    subject_id=None,
                )
            )
        self.assertEqual(0, result, output.getvalue())
        policy = json.loads((partial / "search-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(read_template("profile.example.json")["subject_id"], policy["subject_id"])

    def test_semantic_append_allows_key_order_and_crlf(self):
        candidate = Path(self.temp.name) / "candidate"
        shutil.copytree(self.root, candidate)
        path = candidate / "facts.jsonl"
        fact = read_template("fact.example.json")
        reordered = dict(reversed(list(fact.items())))
        path.write_bytes((json.dumps(reordered) + "\r\n").encode("utf-8"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = core.cmd_verify_append(
                Namespace(base=str(self.root), candidate=str(candidate), json=True)
            )
        self.assertEqual(0, result, output.getvalue())

    def test_semantic_append_rejects_edited_baseline(self):
        candidate = Path(self.temp.name) / "candidate"
        shutil.copytree(self.root, candidate)
        fact = read_template("fact.example.json")
        fact["value"]["result"] = "Edited history"
        write_jsonl(candidate / "facts.jsonl", [fact])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = core.cmd_verify_append(
                Namespace(base=str(self.root), candidate=str(candidate), json=True)
            )
        self.assertEqual(1, result)
        self.assertIn("append.prefix_changed", output.getvalue())

    def test_fit_score_separates_coverage_from_priority(self):
        analysis = read_template("opportunity-analysis.example.json")
        path = Path(self.temp.name) / "analysis.json"
        write_json(path, analysis)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = core.cmd_score_fit(Namespace(analysis=str(path)))
        payload = json.loads(output.getvalue())
        self.assertEqual(0, result)
        self.assertEqual("clarify", payload["recommendation_gate"])
        self.assertNotEqual(payload["coverage_percent"], payload["fit_on_known_percent"])
        self.assertIn("not a hiring probability", payload["interpretation"])

    def test_claim_manifest_accepts_active_supported_fact(self):
        manifest = PLUGIN_ROOT / "templates" / "claim-manifest.example.json"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = core.cmd_validate_claims(
                Namespace(
                    facts=str(self.root / "facts.jsonl"),
                    evidence=str(self.root / "evidence.jsonl"),
                    manifest=str(manifest),
                    json=True,
                    strict_warnings=False,
                )
            )
        self.assertEqual(0, result, output.getvalue())


if __name__ == "__main__":
    unittest.main()
