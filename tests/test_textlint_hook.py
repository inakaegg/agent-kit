import importlib.util
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]


def load_hook():
    spec = importlib.util.spec_from_file_location("textlint_hook", KIT_ROOT / "scripts" / "textlint-hook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(d: str, name: str, text: str) -> Path:
    p = Path(d) / name
    p.write_text(text, encoding="utf-8")
    return p


class IsJapaneseDocumentTest(unittest.TestCase):
    def test_english_only_is_skipped(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "README.md", "# Title\n\nPlain English, with commas, and more.\n")
            self.assertFalse(hook.is_japanese_document(p))

    def test_english_readme_with_japanese_cross_link_is_skipped(self):
        hook = load_hook()
        body = "# pair-watch\n\n日本語: [README.ja.md](README.ja.md)\n\n" + ("Plain English prose about the tool. " * 20)
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(hook.is_japanese_document(write(d, "README.md", body)))

    def test_japanese_documents_are_linted(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as d:
            for name, text in (
                ("ja.md", "日本語の文です。"),
                ("kana.md", "カタカナだけ"),
                ("mixed.md", "README.md を英語正とし、日本語版を README.ja.md へ移す。"),
            ):
                self.assertTrue(hook.is_japanese_document(write(d, name, text)), name)


class PerlAndPythonAgreeTest(unittest.TestCase):
    """pre-commit（perl）と textlint-hook.py（python）の日本語文書判定が同じ結果を返すこと。"""

    FIXTURES = (
        "Plain English only.\n",
        "# pair-watch\n\n日本語: [README.ja.md](README.ja.md)\n\n" + ("English prose. " * 40),
        "日本語の文です。",
        "カタカナだけ",
        "々〜｡ｱｲｳ ＡＢＣ ー・\n",
        "working memory。product specificationの正本ではない。\n" + ("The quick brown fox. " * 20),
        "",
    )

    def test_same_verdict(self):
        import re
        import shutil
        import subprocess
        if shutil.which("perl") is None:
            self.skipTest("perl not available")
        hook = load_hook()
        src = (KIT_ROOT / "git-hooks" / "pre-commit").read_text(encoding="utf-8")
        m = re.search(r"perl -CSD -ne '([^']+)'", src)
        self.assertIsNotNone(m, "pre-commit のperl判定式が見つからない")
        expr = m.group(1)
        with tempfile.TemporaryDirectory() as d:
            for i, text in enumerate(self.FIXTURES):
                p = write(d, f"f{i}.md", text)
                py = hook.is_japanese_document(p)
                pl = subprocess.run(["perl", "-CSD", "-ne", expr, str(p)]).returncode == 0
                self.assertEqual(py, pl, f"fixture {i}: python={py} perl={pl}")


class EditedMarkdownPathsTest(unittest.TestCase):
    """CLIごとに違うhook入力から、lint対象の .md を同じ形で取り出せること。"""

    def test_claude_file_path_is_used_as_is(self):
        hook = load_hook()
        payload = {"tool_name": "Edit", "cwd": "/repo", "tool_input": {"file_path": "/repo/docs/a.md"}}
        self.assertEqual(hook.edited_markdown_paths(payload), [Path("/repo/docs/a.md")])

    def test_claude_non_markdown_is_ignored(self):
        hook = load_hook()
        payload = {"tool_name": "Write", "tool_input": {"file_path": "/repo/src/app.py"}}
        self.assertEqual(hook.edited_markdown_paths(payload), [])

    def test_codex_apply_patch_add_and_update(self):
        hook = load_hook()
        patch = (
            "*** Begin Patch\n"
            "*** Add File: docs/new.md\n+# 新規\n"
            "*** Update File: README.ja.md\n@@\n-旧\n+新\n"
            "*** Update File: src/app.py\n@@\n-a\n+b\n"
            "*** Delete File: docs/old.md\n"
            "*** End Patch\n"
        )
        payload = {"tool_name": "apply_patch", "cwd": "/repo", "tool_input": {"command": patch}}
        self.assertEqual(
            hook.edited_markdown_paths(payload),
            [Path("/repo/docs/new.md"), Path("/repo/README.ja.md")],
        )

    def test_codex_apply_patch_move_uses_destination(self):
        hook = load_hook()
        patch = (
            "*** Begin Patch\n"
            "*** Update File: docs/draft.md\n*** Move to: docs/final.md\n@@\n-x\n+y\n"
            "*** End Patch\n"
        )
        payload = {"tool_name": "apply_patch", "cwd": "/repo", "tool_input": {"command": patch}}
        self.assertEqual(hook.edited_markdown_paths(payload), [Path("/repo/docs/final.md")])

    def test_codex_absolute_path_is_kept(self):
        hook = load_hook()
        patch = "*** Begin Patch\n*** Update File: /elsewhere/x.md\n@@\n-a\n+b\n*** End Patch\n"
        payload = {"tool_name": "apply_patch", "cwd": "/repo", "tool_input": {"command": patch}}
        self.assertEqual(hook.edited_markdown_paths(payload), [Path("/elsewhere/x.md")])

    def test_bash_tool_with_patch_like_text_is_ignored(self):
        hook = load_hook()
        payload = {"tool_name": "Bash", "cwd": "/repo", "tool_input": {"command": "*** Update File: a.md"}}
        self.assertEqual(hook.edited_markdown_paths(payload), [])


class MainExitCodeTest(unittest.TestCase):
    """本体をCLIとして流したときの終了コード（textlint未導入でも成立する経路）。"""

    def run_hook(self, payload) -> int:
        import json
        import subprocess
        result = subprocess.run(
            ["python3", str(KIT_ROOT / "scripts" / "textlint-hook.py")],
            input=json.dumps(payload), capture_output=True, text=True,
        )
        return result.returncode

    def test_missing_file_and_non_dict_payload_pass(self):
        self.assertEqual(self.run_hook({"tool_name": "apply_patch", "cwd": "/nonexistent",
                                        "tool_input": {"command": "*** Add File: a.md\n+x\n"}}), 0)
        self.assertEqual(self.run_hook(["not", "a", "dict"]), 0)


class StdinIntegrationTest(unittest.TestCase):
    def test_real_stdin_calls_linter_for_every_codex_target(self):
        import json, os, subprocess, sys
        with tempfile.TemporaryDirectory(prefix="hook-fixture-", dir=KIT_ROOT) as d:
            root = Path(d)
            for name in ("first.md", "moved.md"):
                (root / name).write_text("日本語の文書です。")
            binary = root / "textlint"
            log = root / "calls.jsonl"
            binary.write_text("#!" + sys.executable + "\nimport json,sys\nfrom pathlib import Path\nwith Path(__file__).with_name('calls.jsonl').open('a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\nprint('fixture finding')\nsys.exit(1)\n")
            binary.chmod(0o755)
            patch = "*** Begin Patch\n*** Add File: first.md\n+本文\n*** Update File: old.md\n*** Move to: moved.md\n@@\n-旧\n+新\n*** End Patch\n"
            payload = dict(hook_event_name="PostToolUse", tool_name="apply_patch", cwd=str(root), tool_input=dict(command=patch))
            result = subprocess.run([sys.executable, str(KIT_ROOT / "scripts/textlint-hook.py")],
                input=json.dumps(payload), env={**os.environ, "PATH": str(root)+os.pathsep+os.environ["PATH"]}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual({Path(json.loads(line)[-1]).name for line in log.read_text().splitlines()}, {"first.md", "moved.md"})


if __name__ == "__main__":
    unittest.main()
