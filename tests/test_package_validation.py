import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.copy = Path(self.temp.name) / "career-skills"
        shutil.copytree(
            ROOT,
            self.copy,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".locks"),
        )

    def tearDown(self):
        self.temp.cleanup()

    def validate(self):
        return subprocess.run(
            [sys.executable, "scripts/validate_package.py"],
            cwd=self.copy,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )

    def test_cursor_manifest_is_required(self):
        (self.copy / ".cursor-plugin" / "plugin.json").unlink()
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(".cursor-plugin/plugin.json", result.stdout)

    def test_cursor_wildcard_is_rejected(self):
        path = self.copy / ".cursor-plugin" / "plugin.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["skills"] = ["skills/*"]
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("wildcard paths are not supported", result.stdout)

    def test_claude_marketplace_parity_is_enforced(self):
        path = self.copy / ".claude-plugin" / "marketplace.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["plugins"][0]["version"] = "9.9.9"
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("marketplace plugin version differs", result.stdout)


if __name__ == "__main__":
    unittest.main()
