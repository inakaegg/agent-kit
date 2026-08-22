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


class ContainsJapaneseTest(unittest.TestCase):
    def test_english_only_is_skipped(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "README.md"
            p.write_text("# Title\n\nPlain English, with commas, and more.\n", encoding="utf-8")
            self.assertFalse(hook.contains_japanese(p))

    def test_japanese_is_linted(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as d:
            for name, text in (("ja.md", "日本語の文です。"), ("kana.md", "カタカナだけ"), ("mixed.md", "English plus 漢字")):
                p = Path(d) / name
                p.write_text(text, encoding="utf-8")
                self.assertTrue(hook.contains_japanese(p), name)


if __name__ == "__main__":
    unittest.main()
