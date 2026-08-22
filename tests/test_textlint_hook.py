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


if __name__ == "__main__":
    unittest.main()
