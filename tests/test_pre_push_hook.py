import os
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
HOOK = KIT_ROOT / "git-hooks" / "pre-push"


def make_repo(check_exit: int) -> Path:
    d = Path(tempfile.mkdtemp())
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    (d / "scripts").mkdir()
    script = d / "scripts" / "agent-check.sh"
    script.write_text(f"#!/bin/sh\nexit {check_exit}\n", encoding="utf-8")
    script.chmod(0o755)
    return d


def run_hook(repo: Path) -> int:
    # push対象なし（stdin空）で起動し、agent-checkの扱いだけを見る
    env = dict(os.environ, GIT_DIR=str(repo / ".git"))
    result = subprocess.run(
        ["sh", str(HOOK), "origin", "https://example.invalid/x.git"],
        cwd=repo, input="", capture_output=True, text=True, env=env,
    )
    return result.returncode


class PrePushAgentCheckTests(unittest.TestCase):
    def test_not_opted_in_never_runs_repo_script(self):
        repo = make_repo(check_exit=1)
        self.assertEqual(run_hook(repo), 0)

    def test_opted_in_failing_script_blocks_push(self):
        repo = make_repo(check_exit=1)
        subprocess.run(["git", "-C", str(repo), "config", "--local", "hooks.runAgentCheck", "true"], check=True)
        self.assertEqual(run_hook(repo), 1)

    def test_opted_in_passing_script_allows_push(self):
        repo = make_repo(check_exit=0)
        subprocess.run(["git", "-C", str(repo), "config", "--local", "hooks.runAgentCheck", "true"], check=True)
        self.assertEqual(run_hook(repo), 0)


if __name__ == "__main__":
    unittest.main()
