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
import os
import re
import subprocess
import sys


# ユーザーの直接指示があるときだけ、remote作成系の遮断を外す印。コマンドの先頭に置く。
USER_DIRECTED = re.compile(r"^\s*AGENT_USER_DIRECTED=1\s")

# remote repositoryの作成・初回push・public化（共通AGENTS.md §3。ユーザー自身が行う）。
# 各規則は1つのコマンド区間（&& ; | 改行で区切った1つ）に対して見る。
GH_API_WRITE = re.compile(
    r"\bgh\s+api\b(?=.*(?:\s(?:-X|--method)\s*(?:PATCH|POST|PUT|DELETE)\b))(?=.*(?:visibility|\bprivate\b))"
    r"|\bgh\s+api\b.*\s(?:-f|-F|--field|--raw-field)\s*(?:visibility|private)="
)
REMOTE_CREATE_RULES = [
    (
        re.compile(r"\bgh\s+repo\s+(?:create|new|fork)\b"),
        "gh repo create / new / fork は禁止（remote repositoryの作成はユーザーが行う。共通AGENTS.md §3）。",
    ),
    (
        re.compile(r"\bgh\s+repo\s+edit\b.*--visibility\b"),
        "gh repo edit --visibility は禁止（公開範囲の変更はユーザーが行う。共通AGENTS.md §3）。",
    ),
    (
        GH_API_WRITE,
        "gh api で visibility / private を書き換えるのは禁止（公開範囲の変更はユーザーが行う。共通AGENTS.md §3）。",
    ),
    (
        re.compile(r"\bgit\s+remote\s+add\b"),
        "git remote add は禁止（remoteの追加と初回pushはユーザーが行う。共通AGENTS.md §3）。",
    ),
]
# 初回push（remoteの無いrepositoryからの -u / --set-upstream）。remoteが既にあるrepositoryでの
# 新しいbranchのpushは、PR作成に必要な通常の操作なので通す。remoteの有無はhookに渡るcwdで見る。
PUSH_SET_UPSTREAM = re.compile(r"\bgit\s+push\b.*\s(?:-u|--set-upstream)(?:\s|$)")
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")


def normalize(command: str) -> str:
    """バックスラッシュ改行の継続行を1行にする。区間の切れ目を跨いだ引数を見落とさないため。"""
    return re.sub(r"\\\r?\n", " ", command)


def has_remote(cwd: str) -> bool:
    """cwdのrepositoryにremoteが1つでもあるか。判定できないときはremote無し（厳しい側）に倒す。"""
    if not cwd or not os.path.isdir(cwd):
        return False
    try:
        # 親から GIT_DIR / GIT_WORK_TREE が渡っていると cwd と別の repository を見てしまうので外す
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        result = subprocess.run(
            ["git", "-C", cwd, "remote"], capture_output=True, text=True, timeout=5, env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() != ""


def remote_create_violation(segment: str, cwd: str) -> str | None:
    for pattern, message in REMOTE_CREATE_RULES:
        if pattern.search(segment):
            return message
    if PUSH_SET_UPSTREAM.search(segment) and not has_remote(cwd):
        return ("remoteの無いrepositoryからの git push -u / --set-upstream は禁止"
                "（初回pushはユーザーが行う。共通AGENTS.md §3）。")
    return None

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
    command = normalize((data.get("tool_input") or {}).get("command") or "")
    cwd = data.get("cwd") or os.getcwd()
    for pattern, message in RULES:
        if pattern.search(command):
            print(f"git-guard: {message}", file=sys.stderr)
            return 2
    directed = bool(USER_DIRECTED.match(command))
    violations = [
        message for segment in SEGMENT_SPLIT.split(command)
        if (message := remote_create_violation(segment, cwd))
    ]
    if not violations:
        return 0
    # ユーザーの直接指示は1つの操作に対するもの。印があっても、remote作成系の区間が2つ以上あれば通さない。
    if directed and len(violations) == 1:
        return 0
    if directed:
        print("git-guard: AGENT_USER_DIRECTED=1 で通せる remote 作成系の操作は1コマンドにつき1つだけ。"
              f"{len(violations)} 件ある: " + " / ".join(violations), file=sys.stderr)
        return 2
    print(f"git-guard: {violations[0]} ユーザーがこの操作を直接指示した場合だけ、"
          "コマンドの先頭に AGENT_USER_DIRECTED=1 を置いて実行する。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
