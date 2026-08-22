from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
        # 公開bundle＝git管理下のファイル（.gitignoreと未追跡はgitの判断に従う）
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--cached"],
            capture_output=True, check=True,
        ).stdout
        for path in (ROOT / p.decode("utf-8") for p in tracked.split(b"\0") if p):
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
