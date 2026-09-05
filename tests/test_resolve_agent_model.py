import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/resolve-agent-model.py"
spec = importlib.util.spec_from_file_location("model_resolver", SCRIPT)
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)
KEY = "REVIEW_MODEL_HEAVY"
FIRST = "codex:model-one(high)"
SECOND = "claude:model-two(medium)"


class ModelResolverTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="model-resolver-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.defaults = self.root / "defaults.env"
        self.defaults.write_text(f"{KEY}={FIRST} {SECOND}\nREVIEW_REQUIRE_OTHER_LINEAGE=false\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def executable(self, name):
        path = self.bin / name
        path.write_text("#!/bin/sh\nexit 99\n")
        path.chmod(0o755)
        return path

    def run_cli(self, *args, script=SCRIPT, env_extra=None):
        env = os.environ.copy()
        env["PATH"] = str(self.bin)
        # The test process itself runs under one CLI or another; hide that so each case chooses.
        env.pop("CLAUDECODE", None)
        env.pop("CODEX_THREAD_ID", None)
        env.update(env_extra or {})
        result = subprocess.run([sys.executable, str(script), "--key", KEY, "--repo", str(self.repo),
                                 "--kit-settings", str(self.defaults), *args],
                                env=env, text=True, capture_output=True)
        return result.returncode, json.loads(result.stdout)

    def test_explicit_model_and_effort_are_not_cli_defaults(self):
        binary = self.executable("codex")
        code, result = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["candidate"], FIRST)
        self.assertEqual(result["argv"][0], str(binary))
        self.assertIn("model-one", result["argv"])
        self.assertIn('model_reasoning_effort="high"', result["argv"])
        self.assertIn("read-only", result["argv"])

    def test_claude_only_selects_second_candidate_without_invoking_it(self):
        self.executable("claude")
        code, result = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["candidate"], SECOND)
        self.assertEqual(result["skipped"], [{"candidate": FIRST, "reason": "missing-cli"}])
        self.assertEqual(result["argv"][result["argv"].index("--effort") + 1], "medium")

    def test_reported_unavailability_falls_back_once(self):
        self.executable("codex")
        self.executable("claude")
        for reason in ("rate-limit", "authentication", "model-unavailable"):
            with self.subTest(reason=reason):
                code, result = self.run_cli("--unavailable", FIRST + "=" + reason)
                self.assertEqual(code, 0)
                self.assertEqual(result["candidate"], SECOND)
                self.assertEqual(result["skipped"][0]["reason"], reason)

    def test_review_findings_and_general_errors_are_not_unavailability(self):
        self.executable("codex")
        for reason in ("changes-requested", "test-failure", "exit-1", "timeout"):
            self.assertEqual(self.run_cli("--unavailable", FIRST + "=" + reason)[0], 2)

    def test_all_unavailable_fails_without_guessing(self):
        code, result = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(len(result["skipped"]), 2)

    def test_tracked_override_wins_and_reports_source(self):
        self.executable("claude")
        path = self.repo / "agent-settings.env"
        path.write_text(f"{KEY}={SECOND}\n")
        code, result = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(Path(result["source"]).resolve(), path.resolve())

    def test_untracked_model_override_is_rejected_even_when_stronger(self):
        self.executable("codex")
        local = self.repo / "agent-settings.local.env"
        for effort in ("low", "xhigh"):
            local.write_text(f"{KEY}=codex:model-one({effort})\n")
            code, result = self.run_cli()
            self.assertEqual(code, 2)
            self.assertIn("tracked agent-settings.env", result["error"])
        local.write_text(f"{KEY}={FIRST} {SECOND}\n")
        self.assertEqual(self.run_cli()[0], 0)

    def test_other_lineage_is_enforced_when_enabled(self):
        self.executable("codex")
        self.executable("claude")
        (self.repo / "agent-settings.env").write_text("REVIEW_REQUIRE_OTHER_LINEAGE=true\n")
        self.assertEqual(self.run_cli()[0], 2)
        code, result = self.run_cli("--implementer-cli", "codex")
        self.assertEqual(code, 0)
        self.assertEqual(result["candidate"], SECOND)
        self.assertFalse(result["provisional"])
        code, result = self.run_cli("--implementer-cli", "codex", "--unavailable", SECOND + "=rate-limit")
        self.assertEqual(code, 0)
        self.assertEqual(result["candidate"], FIRST)
        self.assertTrue(result["provisional"])

    def test_callers_cli_goes_first_unless_other_lineage_is_required(self):
        self.executable("codex")
        self.executable("claude")
        # Explicit flag, then auto-detection from the session's environment.
        code, result = self.run_cli("--primary-cli", "claude")
        self.assertEqual((code, result["candidate"], result["primary_cli"]), (0, SECOND, "claude"))
        self.assertEqual(result["ordering"], "primary-cli")
        code, result = self.run_cli(env_extra={"CLAUDECODE": "1"})
        self.assertEqual((code, result["candidate"]), (0, SECOND))
        code, result = self.run_cli(env_extra={"CODEX_THREAD_ID": "t"})
        self.assertEqual((code, result["candidate"]), (0, FIRST))
        code, result = self.run_cli()
        self.assertEqual((code, result["candidate"], result["primary_cli"]), (0, FIRST, None))
        # Nested launch (both variables set): ambiguous, so the configured order stands.
        code, result = self.run_cli(env_extra={"CLAUDECODE": "1", "CODEX_THREAD_ID": "t"})
        self.assertEqual((code, result["candidate"], result["primary_cli"]), (0, FIRST, None))
        self.assertEqual(result["ordering"], "configured")
        code, result = self.run_cli("--primary-cli", "claude", env_extra={"CLAUDECODE": "1", "CODEX_THREAD_ID": "t"})
        self.assertEqual((code, result["candidate"]), (0, SECOND))
        # Reordering only moves whole CLIs; the written order survives within each CLI.
        third, fourth = "claude:model-three(low)", "codex:model-four(low)"
        self.defaults.write_text(f"{KEY}={FIRST} {SECOND} {third} {fourth}\nREVIEW_REQUIRE_OTHER_LINEAGE=false\n")
        code, result = self.run_cli("--primary-cli", "claude", "--unavailable", SECOND + "=rate-limit")
        self.assertEqual((code, result["candidate"]), (0, third))
        code, result = self.run_cli("--primary-cli", "claude", "--unavailable", SECOND + "=rate-limit",
                                    "--unavailable", third + "=rate-limit")
        self.assertEqual((code, result["candidate"]), (0, FIRST))
        self.defaults.write_text(f"{KEY}={FIRST} {SECOND}\nREVIEW_REQUIRE_OTHER_LINEAGE=false\n")
        # A heavy-risk review with the other lineage required ignores the caller's CLI.
        (self.repo / "agent-settings.env").write_text("REVIEW_REQUIRE_OTHER_LINEAGE=true\n")
        code, result = self.run_cli("--implementer-cli", "codex", "--primary-cli", "codex")
        self.assertEqual((code, result["candidate"], result["provisional"]), (0, SECOND, False))
        self.assertEqual(result["ordering"], "other-lineage")

    def test_ambiguous_empty_or_shell_text_is_rejected_not_executed(self):
        self.executable("codex")
        marker = self.root / "must-not-exist"
        for value in ("", "codex(xhigh)", "any", "codex:m(wrong)", f"$(touch {marker})"):
            self.defaults.write_text(f"{KEY}={value}\nREVIEW_REQUIRE_OTHER_LINEAGE=false\n")
            self.assertEqual(self.run_cli()[0], 2)
            self.assertFalse(marker.exists())

    def test_binary_path_with_spaces_stays_one_argument(self):
        binary = self.executable("codex with spaces")
        code, result = self.run_cli("--codex-bin", str(binary))
        self.assertEqual(code, 0)
        self.assertEqual(result["argv"][0], str(binary))

    def test_generation_and_standalone_skills(self):
        subprocess.run([sys.executable, str(ROOT / "scripts/sync-model-resolver.py"), "--check"], check=True,
                       capture_output=True)
        self.executable("codex")
        for name in ("independent-review", "docs-maintenance"):
            with self.subTest(skill=name):
                copy = self.root / name
                shutil.copytree(ROOT / "skills" / name, copy)
                script = copy / "scripts/resolve-agent-model.py"
                env = os.environ.copy()
                env["PATH"] = str(self.bin)
                env.pop("CLAUDECODE", None)
                env.pop("CODEX_THREAD_ID", None)
                result = subprocess.run([sys.executable, str(script), "--key", "REVIEW_MODEL_READABILITY",
                                         "--repo", str(self.repo)], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(Path(json.loads(result.stdout)["source"]).resolve(),
                                 (copy / "references/model-defaults.env").resolve())


if __name__ == "__main__":
    unittest.main()
