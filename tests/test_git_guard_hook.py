import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
HOOK = KIT_ROOT / "scripts" / "git-guard-hook.py"


# 試験用 repository を作る git は、親の GIT_DIR 等を継がない（suite の隔離試験がそれを見張る）
GIT_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, env=GIT_ENV, capture_output=True)


def run_hook(tool_name: str, command: str, cwd: str | None = None) -> int:
    body = {"tool_name": tool_name, "tool_input": {"command": command}}
    if cwd is not None:
        body["cwd"] = cwd
    payload = json.dumps(body)
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

    def test_codex_shaped_payload_is_blocked_too(self):
        # Codex hooks は同じ tool_name / tool_input.command に加えて
        # hook_event_name・turn_id 等を載せる。余分な項目があっても判定は変わらない。
        payload = json.dumps({
            "session_id": "s", "turn_id": "t", "cwd": "/repo",
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": "git add -A && git commit -m x --no-verify"},
        })
        result = subprocess.run(
            ["python3", str(HOOK)], input=payload, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)

    # §3: remote repositoryの作成・初回push・public化はユーザーが行う
    def test_gh_repo_create_is_blocked(self):
        self.assertEqual(run_hook("Bash", "cd /tmp/x && gh repo create me/x --private --source . --push"), 2)

    def test_gh_repo_edit_visibility_is_blocked(self):
        self.assertEqual(run_hook("Bash", "gh repo edit me/x --visibility public --accept-visibility-change-consequences"), 2)

    def test_gh_api_visibility_is_blocked(self):
        self.assertEqual(run_hook("Bash", "gh api -X PATCH repos/me/x -f visibility=public"), 2)

    def test_git_push_set_upstream_is_blocked_without_a_remote(self):
        with tempfile.TemporaryDirectory() as d:
            git("init", "-q", d)
            self.assertEqual(run_hook("Bash", "git push -u origin main", cwd=d), 2)
            self.assertEqual(run_hook("Bash", "git push --set-upstream origin feat/x", cwd=d), 2)
        # cwd が repository でない・無いときも厳しい側（遮断）に倒す
        self.assertEqual(run_hook("Bash", "git push -u origin main", cwd="/nonexistent/dir"), 2)

    def test_git_push_set_upstream_passes_when_a_remote_exists(self):
        with tempfile.TemporaryDirectory() as d:
            git("init", "-q", d)
            git("-C", d, "remote", "add", "origin", "https://example.invalid/x.git")
            self.assertEqual(run_hook("Bash", "git push -u origin feat/x", cwd=d), 0)

    def test_gh_repo_new_and_fork_are_blocked(self):
        self.assertEqual(run_hook("Bash", "gh repo new project --public"), 2)
        self.assertEqual(run_hook("Bash", "gh repo fork owner/project --clone=false"), 2)

    def test_continuation_lines_are_normalized(self):
        self.assertEqual(run_hook("Bash", "gh repo edit me/x \\\n  --visibility public"), 2)
        self.assertEqual(run_hook("Bash", "gh api -X PATCH repos/me/x \\\n  -f visibility=public"), 2)

    def test_gh_api_read_only_passes(self):
        self.assertEqual(run_hook("Bash", "gh api repos/acme/widget --jq .visibility"), 0)
        self.assertEqual(run_hook("Bash", "gh api repos/acme/private-tools"), 0)

    def test_gh_api_write_of_visibility_is_blocked(self):
        self.assertEqual(run_hook("Bash", "gh api -X PATCH repos/me/x -f private=false"), 2)
        self.assertEqual(run_hook("Bash", "gh api --method PATCH repos/me/x --field visibility=public"), 2)

    def test_user_directed_prefix_covers_only_one_operation(self):
        self.assertEqual(run_hook("Bash", "AGENT_USER_DIRECTED=1 gh repo create A --private && gh repo edit B --visibility public"), 2)
        self.assertEqual(run_hook("Bash", "AGENT_USER_DIRECTED=1 cd /tmp/a && gh repo create me/a --private --source . --push"), 0)

    def test_git_remote_add_is_blocked(self):
        self.assertEqual(run_hook("Bash", "git remote add origin git@github.com:me/x.git"), 2)

    def test_plain_push_to_existing_upstream_passes(self):
        self.assertEqual(run_hook("Bash", "git push origin feat/x"), 0)
        self.assertEqual(run_hook("Bash", "git push"), 0)

    def test_gh_repo_view_and_other_edits_pass(self):
        self.assertEqual(run_hook("Bash", "gh repo view me/x --json visibility"), 0)
        self.assertEqual(run_hook("Bash", "gh repo edit me/x --description 'x'"), 0)

    def test_user_directed_prefix_allows_remote_create(self):
        self.assertEqual(run_hook("Bash", "AGENT_USER_DIRECTED=1 gh repo create me/x --private --source . --push"), 0)
        with tempfile.TemporaryDirectory() as d:
            git("init", "-q", d)
            self.assertEqual(run_hook("Bash", "AGENT_USER_DIRECTED=1 git push -u origin main", cwd=d), 0)

    def test_user_directed_prefix_does_not_unlock_other_rules(self):
        self.assertEqual(run_hook("Bash", "AGENT_USER_DIRECTED=1 git add --all"), 2)

    def test_invalid_json_passes(self):
        result = subprocess.run(
            ["python3", str(HOOK)], input="not json", capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
