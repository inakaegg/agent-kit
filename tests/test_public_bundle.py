from __future__ import annotations

import importlib.util
import contextlib
import io
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]




def load_validate_kit():
    spec = importlib.util.spec_from_file_location("validate_kit", ROOT / "scripts" / "validate-kit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstructionSizeTests(unittest.TestCase):
    def validate(self, agents: str, claude: str = "", newline: str = "\n") -> str:
        vk = load_validate_kit()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in (("AGENTS.md", agents), ("CLAUDE.md", claude)):
                (root / name).write_bytes(content.replace("\n", newline).encode("utf-8"))
            error = io.StringIO()
            with patch.object(vk, "ROOT", root), contextlib.redirect_stderr(error):
                try:
                    vk.validate_agents_size()
                except SystemExit as exc:
                    self.assertEqual(exc.code, 1)
                    return error.getvalue()
            return ""

    @staticmethod
    def agents_text(characters: int, trailing_newline: bool) -> str:
        suffix = "\n" * 59 + ("終\n" if trailing_newline else "終")
        return "規" * (characters - len(suffix)) + suffix

    def test_character_limits_and_newline_normalization(self):
        for newline in ("\n", "\r\n", "\r"):
            for trailing_newline in (False, True):
                for name, limit in (("AGENTS.md", 11000), ("CLAUDE.md", 2000)):
                    for delta in (-1, 0, 1):
                        with self.subTest(newline=newline, trailing=trailing_newline,
                                          name=name, delta=delta):
                            if name == "AGENTS.md":
                                agents = self.agents_text(limit + delta, trailing_newline)
                                claude = ""
                            else:
                                agents = self.agents_text(120, False)
                                claude = "文" * (limit + delta - int(trailing_newline))
                                claude += "\n" if trailing_newline else ""
                            error = self.validate(agents, claude, newline)
                            if delta > 0:
                                self.assertIn(name, error)
                                self.assertIn(str(limit + 1), error)
                                self.assertIn(str(limit), error)
                            else:
                                self.assertEqual(error, "")

    def test_existing_line_limits(self):
        for count in (59, 60, 160, 161):
            for trailing_newline in (False, True):
                with self.subTest(count=count, trailing=trailing_newline):
                    agents = "\n".join(["規"] * count) + ("\n" if trailing_newline else "")
                    error = self.validate(agents)
                    if count in (59, 161):
                        self.assertIn("AGENTS.md", error)
                        self.assertIn(str(count), error)
                    else:
                        self.assertEqual(error, "")


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
            subprocess.run(["git", "-C", str(outer), "init", "-q"], check=True, env=vk.git_env())
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
        self.assertIn("`templates/TASK.md`", text)
        self.assertIn("`docs/instruction-placement.md`", text)
        self.assertIn(
            "`docs/policies/git-and-remote.md`",
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
