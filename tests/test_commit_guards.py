import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
COMMIT_MSG_HOOK = KIT_ROOT / "git-hooks" / "commit-msg"
PRE_COMMIT_HOOK = KIT_ROOT / "git-hooks" / "pre-commit"


def clean_env() -> dict:
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return env


def make_repo(case: unittest.TestCase) -> Path:
    d = Path(tempfile.mkdtemp())
    case.addCleanup(shutil.rmtree, d, True)
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True, env=clean_env())
    return d


def write_settings(repo: Path, line: str, local: bool = False) -> None:
    name = "agent-settings.local.env" if local else "agent-settings.env"
    (repo / name).write_text(line + "\n", encoding="utf-8")


def run_commit_msg(repo: Path, subject: str) -> int:
    msg = repo / "msg.txt"
    msg.write_text(subject + "\n", encoding="utf-8")
    result = subprocess.run(
        ["sh", str(COMMIT_MSG_HOOK), str(msg)],
        cwd=repo, capture_output=True, text=True, env=clean_env(),
    )
    return result.returncode


class CommitMsgSubjectLangTests(unittest.TestCase):
    def test_english_then_japanese_passes(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, "Add feature / 機能を追加"), 0)

    def test_japanese_first_is_rejected(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, "機能を追加 / Add feature"), 1)

    def test_japanese_without_slash_is_rejected(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, "Fix: 説明を修正"), 1)

    def test_english_only_passes(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, "English only subject"), 0)

    def test_merge_subject_is_exempt(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, "Merge branch 'feature/日本語'"), 0)

    def test_opt_out_config_skips_check(self):
        repo = make_repo(self)
        subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "hooks.skipSubjectLang", "true"],
            check=True, env=clean_env(),
        )
        self.assertEqual(run_commit_msg(repo, "日本語だけの件名"), 0)

    def test_repo_settings_select_japanese_first(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=ja-en")
        self.assertEqual(run_commit_msg(repo, "機能を追加 / Add feature"), 0)
        self.assertEqual(run_commit_msg(repo, "Add feature / 機能を追加"), 1)

    def test_repo_settings_select_english_first_explicitly(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=en-ja")
        self.assertEqual(run_commit_msg(repo, "Add feature / 機能を追加"), 0)
        self.assertEqual(run_commit_msg(repo, "機能を追加 / Add feature"), 1)

    def test_japanese_first_still_needs_a_slash(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=ja-en")
        self.assertEqual(run_commit_msg(repo, "機能を追加"), 1)

    def test_japanese_first_rejects_japanese_on_both_sides(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=ja-en")
        self.assertEqual(run_commit_msg(repo, "機能を追加 / 機能の追加"), 1)

    def test_english_only_passes_in_japanese_first_order(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=ja-en")
        self.assertEqual(run_commit_msg(repo, "English only subject"), 0)

    def test_settings_off_skips_check(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=off")
        self.assertEqual(run_commit_msg(repo, "日本語だけの件名"), 0)

    def test_local_settings_override_repo_settings(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=en-ja")
        write_settings(repo, "COMMIT_LANG_ORDER=ja-en", local=True)
        self.assertEqual(run_commit_msg(repo, "機能を追加 / Add feature"), 0)

    def test_invalid_setting_is_rejected(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        # 設定の誤りを黙って既定へ倒すと、効いていない設定に気づけない。
        self.assertEqual(run_commit_msg(repo, "Add feature / 機能を追加"), 1)

    # 設定値の検証は、検査が実際に走ると決まってからにする。除外の側で先に抜ける経路まで
    # 不正値で止めると、設定ミス1つでrebaseの再生やmerge commitが塞がり復旧できなくなる。
    def test_invalid_setting_does_not_block_rebase_replay(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        (repo / ".git" / "rebase-merge").mkdir()
        self.assertEqual(run_commit_msg(repo, "機能を追加 / Add feature"), 0)

    def test_invalid_setting_does_not_block_opted_out_repo(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "hooks.skipSubjectLang", "true"],
            check=True, env=clean_env(),
        )
        self.assertEqual(run_commit_msg(repo, "日本語だけの件名"), 0)

    def test_invalid_setting_does_not_block_merge_subject(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        self.assertEqual(run_commit_msg(repo, "Merge branch 'feature/日本語'"), 0)

    def test_invalid_setting_does_not_block_english_only_subject(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        self.assertEqual(run_commit_msg(repo, "English only subject"), 0)


JA_SUBJECT = "Add feature / 機能を追加"


def body_msg(*body_lines: str, subject: str = JA_SUBJECT) -> str:
    return subject + "\n\n" + "\n".join(body_lines)


class CommitMsgBodyLangTests(unittest.TestCase):
    def test_english_then_japanese_body_passes(self):
        repo = make_repo(self)
        msg = body_msg(
            "Explain the change in English.",
            "",
            "変更内容を日本語で説明する。",
            "",
            "Co-Authored-By: Someone <a@example.com>",
        )
        self.assertEqual(run_commit_msg(repo, msg), 0)

    def test_english_only_body_is_rejected(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, body_msg("English only body.")), 1)

    def test_japanese_only_body_is_rejected(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, body_msg("日本語だけの本文。")), 1)

    def test_japanese_first_body_is_rejected_by_default(self):
        repo = make_repo(self)
        msg = body_msg("日本語の説明。", "", "English explanation.")
        self.assertEqual(run_commit_msg(repo, msg), 1)

    # キーは件名と共通なので、ja-en設定のテストは件名もja-en順にする。
    def test_ja_en_setting_accepts_japanese_first_body(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=ja-en")
        msg = body_msg("日本語の説明。", "", "English explanation.",
                       subject="機能を追加 / Add feature")
        self.assertEqual(run_commit_msg(repo, msg), 0)

    def test_ja_en_setting_rejects_english_first_body(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=ja-en")
        msg = body_msg("English explanation.", "", "日本語の説明。",
                       subject="機能を追加 / Add feature")
        self.assertEqual(run_commit_msg(repo, msg), 1)

    def test_off_skips_body_check(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=off")
        self.assertEqual(run_commit_msg(repo, body_msg("English only body.")), 0)

    def test_bodyless_commit_passes(self):
        repo = make_repo(self)
        self.assertEqual(run_commit_msg(repo, JA_SUBJECT), 0)

    def test_trailer_and_separator_only_body_passes(self):
        repo = make_repo(self)
        msg = body_msg("---", "Co-Authored-By: Someone <a@example.com>")
        self.assertEqual(run_commit_msg(repo, msg), 0)

    def test_trailer_without_space_after_colon_is_excluded(self):
        # Gitのtrailer構文はコロン後の空白が任意。
        repo = make_repo(self)
        msg = body_msg("Signed-off-by:Someone <a@example.com>")
        self.assertEqual(run_commit_msg(repo, msg), 0)

    def test_key_like_line_mid_body_counts_as_body(self):
        # 末尾ブロック以外の「Key: ...」行はtrailerではなく本文（英語側）と数える。
        repo = make_repo(self)
        msg = body_msg("Reason: Explain the change.", "", "変更理由を日本語で説明する。")
        self.assertEqual(run_commit_msg(repo, msg), 0)

    def test_key_like_line_mid_body_still_requires_japanese(self):
        repo = make_repo(self)
        msg = body_msg(
            "Reason: Explain the change.",
            "",
            "More English detail.",
            "",
            "Co-Authored-By: Someone <a@example.com>",
        )
        self.assertEqual(run_commit_msg(repo, msg), 1)

    def test_english_subject_body_is_not_checked(self):
        repo = make_repo(self)
        msg = body_msg("English only body.", subject="English only subject")
        self.assertEqual(run_commit_msg(repo, msg), 0)

    def test_skip_body_lang_config_opts_out(self):
        repo = make_repo(self)
        subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "hooks.skipBodyLang", "true"],
            check=True, env=clean_env(),
        )
        self.assertEqual(run_commit_msg(repo, body_msg("English only body.")), 0)

    def test_invalid_setting_is_rejected(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        msg = body_msg("English body.", "", "日本語の本文。")
        self.assertEqual(run_commit_msg(repo, msg), 1)

    # キー統合により、日本語件名では不正値が件名検査の側で先に拒否される。
    # 本文検査のfail-open（検査対象がなければ設定値を読まない）は、件名検査が
    # 走らない英語件名のbodyless commitで確認する。
    def test_invalid_setting_rejects_japanese_subject_bodyless_commit(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        self.assertEqual(run_commit_msg(repo, JA_SUBJECT), 1)

    def test_invalid_setting_does_not_block_english_bodyless_commit(self):
        repo = make_repo(self)
        write_settings(repo, "COMMIT_LANG_ORDER=japanese-first")
        self.assertEqual(run_commit_msg(repo, "English only subject"), 0)


class PreCommitBranchGuardTests(unittest.TestCase):
    # pre-commit全体（gitleaks等）を通すと環境依存になるため、
    # hookをそのままcommit経由では走らせず、guard部分の挙動をdetach状態の
    # git commit 実行で確認する。gitleaks・textlintが無い環境でも
    # branch guardは最初に走り、detachedなら他の検査より先に止まる。
    def _repo_with_commit(self) -> Path:
        repo = make_repo(self)
        env = clean_env()
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.invalid"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath", str(PRE_COMMIT_HOOK.parent)], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "hooks.skipTextlint", "true"], check=True, env=env)
        # main guard（mainでの非文書commit拒否）を避け、branch guard自体の挙動だけを見る
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "work"], check=True, env=env)
        (repo / "f.txt").write_text("a\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "Initial commit"], check=True, env=env)
        return repo

    def _commit(self, repo: Path, message: str) -> int:
        env = clean_env()
        (repo / "f.txt").open("a", encoding="utf-8").write("b\n")
        subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True, env=env)
        result = subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", message],
            capture_output=True, text=True, env=env,
        )
        return result.returncode

    def test_commit_on_branch_passes(self):
        repo = self._repo_with_commit()
        self.assertEqual(self._commit(repo, "On branch / branch上のcommit"), 0)

    def test_commit_on_detached_head_is_rejected(self):
        repo = self._repo_with_commit()
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--detach", "HEAD"], check=True, env=clean_env())
        self.assertNotEqual(self._commit(repo, "Detached / 分離状態"), 0)

    def test_detached_head_allowed_by_config(self):
        repo = self._repo_with_commit()
        env = clean_env()
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--detach", "HEAD"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "--local", "hooks.allowDetachedHead", "true"], check=True, env=env)
        self.assertEqual(self._commit(repo, "Detached allowed / 許可済み"), 0)


class PreCommitMainGuardTests(unittest.TestCase):
    def _repo(self, branch: str) -> Path:
        repo = make_repo(self)
        env = clean_env()
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.invalid"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath", str(PRE_COMMIT_HOOK.parent)], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "hooks.skipTextlint", "true"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", branch], check=True, env=env)
        return repo

    def _commit_file(self, repo: Path, name: str) -> int:
        env = clean_env()
        (repo / name).write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", name], check=True, env=env)
        result = subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "Add file / ファイルを追加"],
            capture_output=True, text=True, env=env,
        )
        return result.returncode

    def test_code_on_main_is_rejected(self):
        repo = self._repo("main")
        self.assertNotEqual(self._commit_file(repo, "app.py"), 0)

    def test_docs_only_on_main_passes(self):
        repo = self._repo("main")
        self.assertEqual(self._commit_file(repo, "note.md"), 0)

    def test_code_on_feature_branch_passes(self):
        repo = self._repo("feat/x")
        self.assertEqual(self._commit_file(repo, "app.py"), 0)

    def test_opt_out_config_allows_code_on_main(self):
        repo = self._repo("main")
        subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "hooks.allowMainCommits", "true"],
            check=True, env=clean_env(),
        )
        self.assertEqual(self._commit_file(repo, "app.py"), 0)


class PreCommitAgentSettingsTests(unittest.TestCase):
    """agent-settings.env（3層トグル）経由のガード制御。"""

    _repo = PreCommitMainGuardTests.__dict__["_repo"]
    _commit_file = PreCommitMainGuardTests.__dict__["_commit_file"]

    def test_dotfile_on_main_passes_by_default(self):
        # kit既定の MAIN_GUARD_EXTRA_DOCS=.* によりdotfileは文書扱い
        repo = self._repo("main")
        self.assertEqual(self._commit_file(repo, ".gitignore"), 0)

    def test_repo_settings_disable_main_guard(self):
        repo = self._repo("main")
        (repo / "agent-settings.env").write_text("MAIN_DOC_GUARD=false\n", encoding="utf-8")
        self.assertEqual(self._commit_file(repo, "app.py"), 0)

    def test_repo_settings_override_extra_docs(self):
        repo = self._repo("main")
        (repo / "agent-settings.env").write_text("MAIN_GUARD_EXTRA_DOCS=LICENSE\n", encoding="utf-8")
        self.assertEqual(self._commit_file(repo, "LICENSE"), 0)
        # 上書きによりkit既定の .* は効かなくなる
        self.assertNotEqual(self._commit_file(repo, ".gitignore"), 0)

    def test_local_settings_override_repo_settings(self):
        repo = self._repo("main")
        (repo / "agent-settings.env").write_text("MAIN_DOC_GUARD=true\n", encoding="utf-8")
        (repo / "agent-settings.local.env").write_text("MAIN_DOC_GUARD=false\n", encoding="utf-8")
        self.assertEqual(self._commit_file(repo, "app.py"), 0)

    def test_code_on_main_still_rejected_with_default_settings(self):
        repo = self._repo("main")
        self.assertNotEqual(self._commit_file(repo, "app.py"), 0)


class PreCommitLinkCheckTests(unittest.TestCase):
    def _repo(self) -> Path:
        repo = make_repo(self)
        env = clean_env()
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.invalid"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath", str(PRE_COMMIT_HOOK.parent)], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "config", "hooks.skipTextlint", "true"], check=True, env=env)
        return repo

    def _commit_md(self, repo: Path, body: str) -> int:
        (repo / "docs").mkdir(exist_ok=True)
        (repo / "docs" / "a.md").write_text(body, encoding="utf-8")
        env = clean_env()
        subprocess.run(["git", "-C", str(repo), "add", "docs/a.md"], check=True, env=env)
        result = subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "Add doc / 文書を追加"],
            capture_output=True, text=True, env=env,
        )
        return result.returncode

    def test_existing_relative_link_passes(self):
        repo = self._repo()
        (repo / "README.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(self._commit_md(repo, "see [readme](../README.md)\n"), 0)

    def test_broken_relative_link_is_rejected(self):
        repo = self._repo()
        self.assertNotEqual(self._commit_md(repo, "see [gone](../missing.md)\n"), 0)

    def test_anchor_suffix_is_stripped(self):
        repo = self._repo()
        (repo / "README.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(self._commit_md(repo, "see [s](../README.md#sec)\n"), 0)

    def test_urls_and_anchors_are_ignored(self):
        repo = self._repo()
        body = "[u](https://example.invalid/x) [a](#local) [m](mailto:x@example.invalid)\n"
        self.assertEqual(self._commit_md(repo, body), 0)

    def test_links_inside_code_fence_are_ignored(self):
        repo = self._repo()
        self.assertEqual(self._commit_md(repo, "```\n[e](../missing.md)\n```\n"), 0)

    def test_opt_out_config_skips_check(self):
        repo = self._repo()
        subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "hooks.skipLinkCheck", "true"],
            check=True, env=clean_env(),
        )
        self.assertEqual(self._commit_md(repo, "see [gone](../missing.md)\n"), 0)

    def test_settings_file_skips_check(self):
        repo = self._repo()
        (repo / "agent-settings.env").write_text("LINKCHECK=false\n", encoding="utf-8")
        self.assertEqual(self._commit_md(repo, "see [gone](../missing.md)\n"), 0)


if __name__ == "__main__":
    unittest.main()
