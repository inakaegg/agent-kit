import json
import subprocess
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
HOOK = KIT_ROOT / "scripts" / "git-guard-hook.py"


def run_hook(tool_name: str, command: str) -> int:
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})
    result = subprocess.run(
        ["python3", str(HOOK)], input=payload, capture_output=True, text=True,
    )
    return result.returncode


class GitGuardHookTests(unittest.TestCase):
    def test_no_verify_on_commit_is_blocked(self):
        self.assertEqual(run_hook("Bash", 'git commit -m "x" --no-verify'), 2)

    def test_no_verify_on_push_is_blocked(self):
        self.assertEqual(run_hook("Bash", "git push --no-verify origin main"), 2)

    def test_git_add_dot_is_blocked(self):
        self.assertEqual(run_hook("Bash", "cd /tmp/x && git add . && git commit -m x"), 2)

    def test_git_add_dash_a_is_blocked(self):
        self.assertEqual(run_hook("Bash", "git add -A"), 2)

    def test_git_add_all_is_blocked(self):
        self.assertEqual(run_hook("Bash", "git add --all"), 2)

    def test_git_add_named_files_pass(self):
        self.assertEqual(run_hook("Bash", "git add src/app.py docs/README.md"), 0)

    def test_git_add_dotfile_passes(self):
        self.assertEqual(run_hook("Bash", "git add .gitignore"), 0)

    def test_plain_commit_passes(self):
        self.assertEqual(run_hook("Bash", 'git commit -m "Add x / xを追加"'), 0)

    def test_git_log_dash_n_passes(self):
        self.assertEqual(run_hook("Bash", "git log -n 5 --oneline"), 0)

    def test_non_bash_tool_passes(self):
        self.assertEqual(run_hook("Read", "git add ."), 0)

    def test_invalid_json_passes(self):
        result = subprocess.run(
            ["python3", str(HOOK)], input="not json", capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
