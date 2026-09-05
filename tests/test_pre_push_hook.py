import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
HOOK = KIT_ROOT / "git-hooks" / "pre-push"


DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")


def clean_env() -> dict:
    # pre-push hookの中から（hooks.runAgentCheck経由で）実行されても、gitが渡すGIT_DIR等に
    # 引きずられず一時リポジトリを見るようにする。global/system configも隔離する。
    env = {k: v for k, v in os.environ.items() if k not in DROP}
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return env


def make_repo(case: unittest.TestCase, check_exit: int) -> Path:
    d = Path(tempfile.mkdtemp())
    case.addCleanup(shutil.rmtree, d, True)
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True, env=clean_env())
    (d / "scripts").mkdir()
    script = d / "scripts" / "agent-check.sh"
    script.write_text(f"#!/bin/sh\nexit {check_exit}\n", encoding="utf-8")
    script.chmod(0o755)
    return d


def run_hook(repo: Path) -> int:
    # push対象なし（stdin空）で起動し、agent-checkの扱いだけを見る
    env = dict(clean_env(), GIT_DIR=str(repo / ".git"))
    result = subprocess.run(
        ["sh", str(HOOK), "origin", "https://example.invalid/x.git"],
        cwd=repo, input="", capture_output=True, text=True, env=env,
    )
    return result.returncode


class PrePushAgentCheckTests(unittest.TestCase):
    def test_not_opted_in_never_runs_repo_script(self):
        repo = make_repo(self, check_exit=1)
        self.assertEqual(run_hook(repo), 0)

    def test_opted_in_failing_script_blocks_push(self):
        repo = make_repo(self, check_exit=1)
        subprocess.run(["git", "-C", str(repo), "config", "--local", "hooks.runAgentCheck", "true"], check=True, env=clean_env())
        self.assertEqual(run_hook(repo), 1)

    def test_opted_in_passing_script_allows_push(self):
        repo = make_repo(self, check_exit=0)
        subprocess.run(["git", "-C", str(repo), "config", "--local", "hooks.runAgentCheck", "true"], check=True, env=clean_env())
        self.assertEqual(run_hook(repo), 0)


    def test_opted_in_script_does_not_inherit_the_hooks_git_environment(self):
        # gitはhookへ GIT_DIR 等を渡す。それが検査scriptの子プロセスまで届くと、使い捨てrepoを
        # 作るテストのgit操作が実repoへ向く（agent-kit e72f8b1 / pair-watch a8020cc で個別対処
        # していた事故）。hookは検査scriptを起動する前にこれらを外す。
        repo = make_repo(self, check_exit=0)
        seen = repo / "seen-env.txt"
        (repo / "scripts" / "agent-check.sh").write_text(
            "#!/bin/sh\nenv | grep '^GIT_' > \"$1\"; exit 0\n".replace("$1", str(seen)), encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "config", "--local", "hooks.runAgentCheck", "true"], check=True, env=clean_env())
        env = dict(clean_env(), GIT_DIR=str(repo / ".git"), GIT_WORK_TREE=str(repo),
                   GIT_INDEX_FILE=str(repo / ".git" / "index"), GIT_PREFIX="")
        result = subprocess.run(["sh", str(HOOK), "origin", "https://example.invalid/x.git"],
                                cwd=repo, input="", capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        leaked = [line.split("=", 1)[0] for line in seen.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([v for v in leaked if v in DROP], [], leaked)
        # gitの動作そのものを決める変数（configの隔離など）は残る
        self.assertIn("GIT_CONFIG_GLOBAL", leaked)

if __name__ == "__main__":
    unittest.main()
