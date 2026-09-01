"""テスト自身がGIT_DIR等の環境変数に引きずられないことを確かめる回帰テスト。

git hookからテストを走らせると、gitがhookへ渡す GIT_DIR / GIT_WORK_TREE などが
子プロセスへ継承される。この状態でテストが `git -C <一時repo>` を呼ぶと、gitは
-C ではなく環境変数の側を優先し、hook元のrepoのconfig・branch・commitを書き換える。

防御は2層ある。ここではその両方を検査する。
  1. scripts/agent-check.sh の入口での一括unset（すべてのテストをまとめて守る）
  2. 各テストがgitを呼ぶときに渡す環境（agent-check.sh を経由しない実行経路のため）
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT_ROOT = Path(__file__).resolve().parents[1]
AGENT_CHECK = KIT_ROOT / "scripts" / "agent-check.sh"

# 隔離すべきキーの正本は scripts/validate-kit.py の GIT_ENV_KEYS_TO_DROP。
GIT_ENV_KEYS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")

# 下の全体実行テストが自分自身を無限に呼び出さないための目印。
CHILD_MARKER = "AGENT_KIT_GIT_ENV_ISOLATION_CHILD"


def load_module(name: str, path: Path):
    """実行の起こし方（discover / -m unittest <path>）に依存せずファイルから読む。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in GIT_ENV_KEYS}
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return env


def git(env: dict, repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True, env=env,
    )
    return result.stdout


class DropListTests(unittest.TestCase):
    """正本の一覧と、各テストが使う隔離ヘルパーの一致を見る。"""

    def test_validate_kit_drop_list_is_the_reference(self):
        module = load_module("validate_kit", KIT_ROOT / "scripts" / "validate-kit.py")
        self.assertEqual(set(module.GIT_ENV_KEYS_TO_DROP), set(GIT_ENV_KEYS))

    def test_agent_check_unsets_every_key(self):
        # 主対策。ここが1行消えると個々のテストの隔離漏れがそのまま事故になる。
        source = AGENT_CHECK.read_text(encoding="utf-8")
        unset_lines = [l for l in source.splitlines() if l.startswith("unset ")]
        self.assertTrue(unset_lines, "agent-check.sh に unset 行がない")
        unset_words = set(" ".join(unset_lines).split())
        for key in GIT_ENV_KEYS:
            self.assertIn(key, unset_words, f"agent-check.sh が {key} を外していない")

    def test_test_helpers_drop_every_key(self):
        # gitを呼ぶテストの隔離ヘルパーが、環境に値があっても落とすことを確かめる。
        helpers = [
            load_module("t_commit_guards", KIT_ROOT / "tests" / "test_commit_guards.py"),
            load_module("t_pre_push_hook", KIT_ROOT / "tests" / "test_pre_push_hook.py"),
        ]
        polluted = {k: "/nonexistent/should-not-leak" for k in GIT_ENV_KEYS}
        with mock.patch.dict(os.environ, polluted):
            for module in helpers:
                # 失敗メッセージへ環境そのものを出さない（環境変数には秘密情報が入り得る）。
                leaked = [k for k in GIT_ENV_KEYS if k in module.clean_env()]
                self.assertEqual(
                    leaked, [],
                    f"{Path(module.__file__).name} の clean_env が {leaked} を落としていない")


class SuiteIgnoresInheritedGitDirTests(unittest.TestCase):
    """使い捨てrepoをGIT_DIRに入れて全テストを回し、そのrepoが無傷かを見る。

    実repoではなく使い捨てのrepoを指すのは、回帰が起きたときに壊れるのが
    テスト用のrepoだけで済むようにするため。観測したい性質は同じ
    （GIT_DIRが指すrepoのconfig・branch・HEADが変わらない）。
    """

    def test_unittest_discover_does_not_touch_the_repo_in_git_dir(self):
        if os.environ.get(CHILD_MARKER):
            self.skipTest("子プロセス側。ここから再帰的に全体実行はしない")

        canary = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, canary, True)
        env = base_env()
        subprocess.run(["git", "init", "-q", "-b", "main", str(canary)],
                       check=True, env=env)
        git(env, canary, "config", "user.email", "t@example.invalid")
        git(env, canary, "config", "user.name", "t")
        (canary / "f.txt").write_text("a\n", encoding="utf-8")
        git(env, canary, "add", "f.txt")
        git(env, canary, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "seed")

        before = (
            git(env, canary, "config", "--local", "-l"),
            git(env, canary, "branch", "--format=%(refname)"),
            git(env, canary, "rev-parse", "HEAD"),
        )

        child = dict(env)
        child[CHILD_MARKER] = "1"
        child["GIT_DIR"] = str(canary / ".git")
        child["GIT_WORK_TREE"] = str(canary)
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(KIT_ROOT / "tests")],
            cwd=str(KIT_ROOT), capture_output=True, text=True, env=child, timeout=900,
        )
        self.assertEqual(
            proc.returncode, 0,
            "GIT_DIRを継承した状態でテストが失敗:\n" + proc.stdout + proc.stderr)

        after = (
            git(env, canary, "config", "--local", "-l"),
            git(env, canary, "branch", "--format=%(refname)"),
            git(env, canary, "rev-parse", "HEAD"),
        )
        self.assertEqual(before[0], after[0], "GIT_DIRのrepoのconfigが書き換わった")
        self.assertEqual(before[1], after[1], "GIT_DIRのrepoのbranchが増減した")
        self.assertEqual(before[2], after[2], "GIT_DIRのrepoのHEADが動いた")


if __name__ == "__main__":
    unittest.main()
