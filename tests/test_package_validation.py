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

    def test_codex_website_must_point_to_catalog(self):
        path = self.copy / ".codex-plugin" / "plugin.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["interface"].pop("websiteURL")
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("website must point to the Plug'n Skills catalog", result.stdout)

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

    def test_claude_marketplace_root_version_parity_is_enforced(self):
        path = self.copy / ".claude-plugin" / "marketplace.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["version"] = "9.9.9"
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("marketplace version differs", result.stdout)

    def test_package_version_parity_is_enforced(self):
        path = self.copy / "package.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["version"] = "9.9.9"
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("package.json version differs", result.stdout)

    def replace_description(self, skill: str, description: str):
        path = self.copy / "skills" / skill / "SKILL.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        lines[2] = f"description: {description}"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_generic_skill_description_lead_is_rejected(self):
        self.replace_description(
            "opportunity-search",
            "Use when the user wants fresh job opportunities from approved sources.",
        )
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("must lead with the owned career capability", result.stdout)

    def test_overlong_skill_description_is_rejected(self):
        self.replace_description("opportunity-search", "Opportunity search " + ("x" * 223))
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("description must contain 1-240 characters", result.stdout)

    def test_skill_description_prefix_collision_is_rejected(self):
        source = self.copy / "skills" / "application-campaign" / "SKILL.md"
        description = source.read_text(encoding="utf-8").splitlines()[2].split(": ", 1)[1]
        self.replace_description("opportunity-search", description[:40] + " with another ending.")
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("description characters collide", result.stdout)

    def test_extra_skill_frontmatter_key_is_rejected(self):
        path = self.copy / "skills" / "opportunity-search" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("---\n\n", "metadata: extra\n---\n\n", 1), encoding="utf-8")
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("unsupported frontmatter keys", result.stdout)

    def test_invalid_plain_yaml_description_is_rejected(self):
        self.replace_description(
            "opportunity-search",
            "Opportunity search: find fresh roles from approved sources.",
        )
        result = self.validate()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("plain frontmatter value", result.stdout)

    def test_crlf_skill_frontmatter_is_supported(self):
        path = self.copy / "skills" / "opportunity-search" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        path.write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))
        result = self.validate()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_ignored_scratch_is_excluded_without_git_metadata(self):
        scratch = self.copy / "tmp" / "runtime-copy"
        scratch.mkdir(parents=True)
        (scratch / "private.md").write_text(
            "machine path " + "C:" + "/Users/example/private.txt\n",
            encoding="utf-8",
        )
        result = self.validate()
        self.assertEqual(0, result.returncode, result.stdout)


if __name__ == "__main__":
    unittest.main()
