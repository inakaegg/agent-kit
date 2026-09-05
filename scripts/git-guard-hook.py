#!/usr/bin/env python3
"""Claude Code / Codex の PreToolUse hook: エージェントのgitコマンドの禁止形を遮断する。

共通AGENTS.mdのうち、git側にhook地点がなく機械強制できない3つを実装する:
  - §5: --no-verify での検査回避の禁止
  - §8: git add . / -A / --all の丸ごとstageの禁止（fileを個別指定する）
  - §3: remote repositoryの作成・初回push・public化の禁止（ユーザー自身が行う）。
    ユーザーがその発話で直接指示したときだけ、コマンドの先頭に AGENT_USER_DIRECTED=1 を
    置いて通す（何を根拠に通したかがコマンドに残る）。

stdinでhook入力(JSON)を受け、Bashのcommand文字列を検査する。両CLIとも
tool_name は "Bash"、コマンドは tool_input.command に入る（他の項目は見ない）。
違反時はexit 2（ブロック。stderrがエージェントへ渡る）、それ以外はexit 0。
人間のターミナル操作には一切効かない（エージェントのツール呼び出し専用）。
登録方法はagent-kit READMEのGit hooks節を参照。
"""
import json
import re
import sys


# ユーザーの直接指示があるときだけ、remote作成系の遮断を外す印。コマンドの先頭に置く。
USER_DIRECTED = re.compile(r"^\s*AGENT_USER_DIRECTED=1\s")

# remote repositoryの作成・初回push・public化（共通AGENTS.md §3。ユーザー自身が行う）
REMOTE_CREATE_RULES = [
    (
        re.compile(r"\bgh\s+repo\s+create\b"),
        "gh repo create は禁止（remote repositoryの作成はユーザーが行う。共通AGENTS.md §3）。",
    ),
    (
        re.compile(r"\bgh\s+repo\s+edit\b[^|;&\n]*--visibility\b"),
        "gh repo edit --visibility は禁止（公開範囲の変更はユーザーが行う。共通AGENTS.md §3）。",
    ),
    (
        re.compile(r"\bgh\s+api\b[^|;&\n]*(?:visibility|\bprivate\b)"),
        "gh api で visibility / private を触るのは禁止（公開範囲の変更はユーザーが行う。共通AGENTS.md §3）。",
    ),
    (
        re.compile(r"\bgit\s+push\b[^|;&\n]*\s(?:-u|--set-upstream)(?:\s|$)"),
        "git push -u / --set-upstream は禁止（初回pushと上流の設定はユーザーが行う。共通AGENTS.md §3）。"
        "既に上流があるbranchへは git push だけを使う。",
    ),
    (
        re.compile(r"\bgit\s+remote\s+add\b"),
        "git remote add は禁止（remoteの追加と初回pushはユーザーが行う。共通AGENTS.md §3）。",
    ),
]

RULES = [
    (
        re.compile(r"\bgit\b[^|;&\n]*\s--no-verify\b"),
        "git の --no-verify は使用禁止（共通AGENTS.md §5）。"
        "hookの指摘を修正してから再実行する。",
    ),
    (
        re.compile(r"\bgit\s+add\s+(?:[^|;&\n]*\s)?(?:\.|\./|-A|--all)(?:\s|$|[|;&])"),
        "git add . / -A / --all は使用禁止（共通AGENTS.md §8）。"
        "stageするfileを個別に指定する。",
    ),
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    for pattern, message in RULES:
        if pattern.search(command):
            print(f"git-guard: {message}", file=sys.stderr)
            return 2
    if not USER_DIRECTED.match(command):
        for pattern, message in REMOTE_CREATE_RULES:
            if pattern.search(command):
                print(f"git-guard: {message} ユーザーがこの操作を直接指示した場合だけ、"
                      "コマンドの先頭に AGENT_USER_DIRECTED=1 を置いて実行する。", file=sys.stderr)
                return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
