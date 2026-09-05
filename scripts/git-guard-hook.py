#!/usr/bin/env python3
"""Claude Code / Codex の PreToolUse hook: エージェントのgitコマンドの禁止形を遮断する。

共通AGENTS.mdのうち、git側にhook地点がなく機械強制できない2つを実装する:
  - §5: --no-verify での検査回避の禁止
  - §8: git add . / -A / --all の丸ごとstageの禁止（fileを個別指定する）

stdinでhook入力(JSON)を受け、Bashのcommand文字列を検査する。両CLIとも
tool_name は "Bash"、コマンドは tool_input.command に入る（他の項目は見ない）。
違反時はexit 2（ブロック。stderrがエージェントへ渡る）、それ以外はexit 0。
人間のターミナル操作には一切効かない（エージェントのツール呼び出し専用）。
登録方法はagent-kit READMEのGit hooks節を参照。
"""
import json
import re
import sys


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
