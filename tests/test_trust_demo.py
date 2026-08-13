import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scripts import run_trust_demo


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_trust_demo.py"


class TrustDemoTest(unittest.TestCase):
    def test_repository_enforces_lf_for_hash_bound_text(self):
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("* text=auto eol=lf", attributes)

    def test_release_core_hash_is_stable_for_crlf_checkout(self):
        source = (ROOT / "scripts" / "career_core.py").read_bytes()
        crlf = source.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "career_core.py"
            path.write_bytes(crlf)
            self.assertEqual(
                run_trust_demo.RELEASE_CORE_SHA256,
                run_trust_demo.normalized_text_sha256(path),
            )

    def test_public_claim_card_matches_fixture_ids_text_and_scope(self):
        manifest = json.loads(
            (ROOT / "examples" / "trust-demo" / "supported-claim-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        fact = json.loads(
            (ROOT / "examples" / "trust-demo" / "facts.jsonl").read_text(
                encoding="utf-8"
            )
        )
        evidence = json.loads(
            (ROOT / "examples" / "trust-demo" / "evidence.jsonl").read_text(
                encoding="utf-8"
            )
        )
        card = (ROOT / "examples" / "trust-demo" / "claim-manifest-card.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(manifest["claims"][0]["text"], card)
        self.assertIn(fact["fact_id"], card)
        self.assertIn(evidence["id"], card)
        self.assertIn(json.dumps(fact["scope"], separators=(",", ":")), card)

    def run_demo(self, output: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(RUNNER), "--output", str(output)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_demo_proves_claim_and_approval_boundaries_deterministically(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            first_run = self.run_demo(first)
            second_run = self.run_demo(second)

            self.assertEqual(0, first_run.returncode, first_run.stderr)
            self.assertEqual(0, second_run.returncode, second_run.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_text(encoding="utf-8"), first_run.stdout)

            receipt = json.loads(first_run.stdout)
            self.assertTrue(receipt["synthetic_data_only"])
            self.assertEqual(
                "42e77fbe5592f1953e6407784bba024e6956f2e7",
                receipt["contract_release_commit"],
            )
            self.assertEqual(
                "eed979cda30ea7788c1772b222d78d1f200bb40a022df36f34cbe705de841a41",
                receipt["contract_core_sha256"],
            )
            self.assertEqual(
                {"passed": 4, "total": 4, "valid": True}, receipt["summary"]
            )
            scenarios = {item["id"]: item for item in receipt["scenarios"]}
            self.assertIn(
                "claim.unsupported",
                scenarios["unsupported_claim_rejected"]["error_codes"],
            )
            self.assertTrue(scenarios["supported_claim_accepted"]["valid"])
            self.assertTrue(scenarios["approved_payload_hash_valid"]["executable"])
            mutation = scenarios["one_byte_payload_mutation_rejected"]
            self.assertEqual(1, mutation["byte_diff_count"])
            self.assertNotEqual(mutation["expected_hash"], mutation["supplied_hash"])
            self.assertIn("plan.approval_hash_mismatch", mutation["error_codes"])


if __name__ == "__main__":
    unittest.main()
