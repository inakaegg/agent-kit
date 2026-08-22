from __future__ import annotations

import importlib.util
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]




def load_validate_kit():
    spec = importlib.util.spec_from_file_location("validate_kit", ROOT / "scripts" / "validate-kit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BundleFilesTests(unittest.TestCase):
    def test_non_git_directory_falls_back_to_rglob(self):
        vk = load_validate_kit()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text("x", encoding="utf-8")
            (root / "_ai").mkdir()
            (root / "_ai" / "internal.md").write_text("x", encoding="utf-8")
            files = vk.bundle_files(root)
            self.assertEqual({p.name for p in files}, {"a.md"})

    def test_subdirectory_of_another_repo_falls_back(self):
        vk = load_validate_kit()
        with tempfile.TemporaryDirectory() as d:
            outer = Path(d)
            subprocess.run(["git", "-C", str(outer), "init", "-q"], check=True)
            (outer / ".gitignore").write_text("kit/\n", encoding="utf-8")
            kit = outer / "kit"
            kit.mkdir()
            (kit / "leak.md").write_text("x", encoding="utf-8")
            files = vk.bundle_files(kit)
            self.assertEqual({p.name for p in files}, {"leak.md"})

class PublicBundleTests(unittest.TestCase):
    def test_global_agents_uses_skill_names_and_explicit_policy_paths(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertNotRegex(text, r"`skills/[^`]+")
        for skill_name in (
            "debug-loop",
            "docs-maintenance",
            "evaluation-loop",
            "independent-review",
            "large-work",
            "pr-review-loop",
            "ui-verification",
        ):
            self.assertIn(f"`${skill_name}`", text)
        self.assertIn("`~/.codex/agent-kit/templates/TASK.md`", text)
        self.assertIn("`~/.codex/agent-kit/docs/instruction-placement.md`", text)
        self.assertIn(
            "`~/.codex/agent-kit/docs/policies/git-and-remote.md`",
            text,
        )
        self.assertIn(
            "`~/.codex/local-policies/local-environment.md`",
            text,
        )

    def test_skills_are_self_contained(self) -> None:
        self.assertTrue(
            (
                ROOT
                / "skills"
                / "docs-maintenance"
                / "references"
                / "documentation.md"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "skills"
                / "independent-review"
                / "assets"
                / "REVIEW_PROMPT.md"
            ).is_file()
        )

    def test_public_bundle_has_no_personal_or_machine_specific_values(self) -> None:
        forbidden = (
            re.compile(r"/" r"Users/[^/\s]+"),
            re.compile(r"/" r"Volumes/"),
            re.compile(r"(?<!github\.com/)\b" + "inaka" + r"egg\b", re.IGNORECASE),
            re.compile(r"\b" + "5237" + r"6271\b"),
        )

        scanned_suffixes = {".md", ".py", ".sh", ".yaml"}
        # 公開bundle＝git管理下のファイル。列挙はvalidate-kitと同じヘルパーを使う。
        files = load_validate_kit().bundle_files()
        self.assertGreater(len(files), 0, "公開bundleの走査対象が0件")
        self.assertIn(ROOT / "README.md", files)
        for path in files:
            if not path.is_file():
                continue
            if path.suffix not in scanned_suffixes and path.parent.name != "git-hooks":
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                self.assertIsNone(
                    pattern.search(text),
                    f"{path.relative_to(ROOT)} contains {pattern.pattern}",
                )

    def test_verification_template_has_one_source(self) -> None:
        self.assertTrue((ROOT / "templates" / "VERIFICATION.md").is_file())
        self.assertFalse((ROOT / "docs" / "quality" / "verification.md").exists())

    def test_claude_adapter_imports_agents_once(self) -> None:
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("@AGENTS.md"), 1)


if __name__ == "__main__":
    unittest.main()
