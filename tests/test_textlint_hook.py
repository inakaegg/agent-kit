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


if __name__ == "__main__":
    unittest.main()
