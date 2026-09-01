import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = KIT_ROOT / "scripts" / "test-squash-guard.sh"

DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")


def clean_env() -> dict:
    # pre-push hookの中から（hooks.runAgentCheck経由で）実行されても、gitが渡すGIT_DIR等に
    # 引きずられず一時リポジトリを見るようにする（tests/test_pre_push_hook.py と同じ扱い）。
    # fixture側でもunsetしているが、入口でも落として二重に守る。
    return {k: v for k, v in os.environ.items() if k not in DROP}


class SquashGuardScenarios(unittest.TestCase):
    """squash guardの再現テスト一式をshellのfixture経由で実行する。

    ケース本体はscripts/test-squash-guard.shにある（一時repoでの
    commit/push操作の連なりはshellのほうが読み書きしやすいため）。
    ここはCI（unittest discover）から確実に走らせるための入口。
    """

    def test_scenarios(self):
        proc = subprocess.run(
            ["sh", str(SCRIPT)], capture_output=True, text=True, timeout=300,
            env=clean_env(),
        )
        self.assertEqual(
            proc.returncode, 0,
            "squash guardの再現テストが失敗:\n" + proc.stdout + proc.stderr,
        )


class MktempFailureTests(unittest.TestCase):
    """一時ディレクトリを作れないときに、/ 直下へ書きに行かず止まることを見る。

    fixtureは以降のパスを "$TMP/..." で組み立てる。TMPが空のまま進むと
    "/bin/gitleaks" のような絶対パスへstubを書き込もうとするため、mktempの
    失敗（と、失敗を伝えず空を返す実装）はその場で止める必要がある。
    """

    def _run_with_mktemp_stub(self, body: str) -> subprocess.CompletedProcess:
        stub_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, stub_dir, True)
        stub = stub_dir / "mktemp"
        stub.write_text(body, encoding="utf-8")
        stub.chmod(0o755)
        env = clean_env()
        env["PATH"] = f"{stub_dir}{os.pathsep}{env.get('PATH', '')}"
        return subprocess.run(
            ["sh", str(SCRIPT)], capture_output=True, text=True, timeout=120, env=env,
        )

    def test_aborts_when_mktemp_fails(self):
        proc = self._run_with_mktemp_stub("#!/bin/sh\nexit 1\n")
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("PASS:", proc.stdout)
        self.assertIn("一時ディレクトリを作成できません", proc.stderr)

    def test_aborts_when_mktemp_returns_nothing(self):
        proc = self._run_with_mktemp_stub("#!/bin/sh\nexit 0\n")
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("PASS:", proc.stdout)
        self.assertIn("一時ディレクトリを作成できません", proc.stderr)


if __name__ == "__main__":
    unittest.main()
