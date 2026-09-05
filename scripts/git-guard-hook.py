#!/usr/bin/env python3
"""Claude Code / Codex の PreToolUse hook: エージェントのgitコマンドの禁止形を遮断する。

共通AGENTS.mdのうち、git側にhook地点がなく機械強制できない3つを実装する:
  - §5: --no-verify での検査回避の禁止
  - §8: git add . / -A / --all の丸ごとstageの禁止（fileを個別指定する）
  - §3: remote repositoryの作成・remoteの無いrepositoryの初回push・public化の禁止
    （ユーザー自身が行う）。ユーザーがその発話で直接指示したときだけ、コマンドの先頭に
    AGENT_USER_DIRECTED=1 を置いて通す（何を根拠に通したかがコマンドに残る）。

stdinでhook入力(JSON)を受け、Bashのcommand文字列を検査する。両CLIとも
tool_name は "Bash"、コマンドは tool_input.command に入る。§3の判定には cwd も使う。
違反時はexit 2（ブロック。stderrがエージェントへ渡る）、それ以外はexit 0。
人間のターミナル操作には一切効かない（エージェントのツール呼び出し専用）。
登録方法はagent-kit READMEのGit hooks節を参照。
"""
import json
import os
import re
import shlex
import subprocess
import sys

# ユーザーの直接指示があるときだけ、remote作成系の遮断を外す印。コマンドの先頭に置く。
USER_DIRECTED = re.compile(r"^\s*AGENT_USER_DIRECTED=1\s")

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

# --- §3 remote repositoryの作成・初回push・public化 ------------------------------------
#
# 文字列の検索ではなく、コマンド区間（&& ; | 改行で区切った1つ）を shell の語に分けてから、
# 先頭の語（と `cd` で移る実効directory）を見る。引用符の中や heredoc の本文に同じ文字列が
# あっても、実行位置に無ければ遮断しない。ただし文字列を別のshellへ渡して実行する形
# （bash -c, eval, xargs 等）は中身を実行位置とみなす。

SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")
URL_LIKE = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|[^/@\s]+@[^/:\s]+:)")
INTERPRETERS = {"bash", "sh", "zsh", "fish", "eval", "exec", "xargs", "env", "nohup", "time",
                "python", "python3", "node", "perl", "ruby", "osascript"}
REPO_UPDATE_ENDPOINT = re.compile(r"^/?repos/[^/\s]+/[^/\s]+/?$")
WRITE_METHODS = {"PATCH", "POST", "PUT", "DELETE"}


def normalize(command: str) -> str:
    """バックスラッシュ改行の継続行を1行にし、heredoc の本文を落とす（実行位置ではない）。"""
    command = re.sub(r"\\\r?\n", " ", command)
    return re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\n.*?\n\1(?=\n|$)", " ", command, flags=re.S)


def has_remote(directory: str | None) -> bool:
    """directoryのrepositoryにremoteが1つでもあるか。判定できないときはremote無し（厳しい側）に倒す。"""
    if not directory or not os.path.isdir(directory):
        return False
    try:
        # 親から GIT_DIR / GIT_WORK_TREE が渡っていると別の repository を見てしまうので外す
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        result = subprocess.run(
            ["git", "-C", directory, "remote"], capture_output=True, text=True, timeout=5, env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() != ""


def split_words(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        # 閉じていない引用符など。語に分けられないものは、そのまま空白で切って厳しい側で見る
        return segment.split()


def strip_env_assignments(words: list[str]) -> list[str]:
    while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
        words = words[1:]
    return words


def resolve_dir(base: str | None, target: str) -> str | None:
    """`cd` の移動先。変数や副shellを含むなど決められないときは None（判定不能）。"""
    if not target or target == "-" or any(ch in target for ch in "$`(<>"):
        return None
    expanded = os.path.expanduser(target)
    if os.path.isabs(expanded):
        return os.path.normpath(expanded)
    if base is None:
        return None
    return os.path.normpath(os.path.join(base, expanded))


def git_effective_dir(words: list[str], current: str | None) -> tuple[str | None, list[str]]:
    """`git -C <dir>` 等のglobal optionを読み、実効directoryとsubcommand以降の語を返す。"""
    i = 1
    directory = current
    while i < len(words):
        w = words[i]
        if w == "-C" and i + 1 < len(words):
            directory = resolve_dir(directory, words[i + 1])
            i += 2
        elif w.startswith("-C") and len(w) > 2:
            directory = resolve_dir(directory, w[2:])
            i += 1
        elif w in ("-c", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(words):
            i += 2
        elif w.startswith("-"):
            i += 1
        else:
            break
    return directory, words[i:]


def check_gh(words: list[str]) -> str | None:
    if len(words) < 2:
        return None
    if words[1] == "repo" and len(words) >= 3:
        if words[2] in ("create", "new", "fork"):
            return "gh repo create / new / fork は禁止（remote repositoryの作成はユーザーが行う。共通AGENTS.md §3）。"
        if words[2] == "edit":
            for j, w in enumerate(words):
                value = None
                if w == "--visibility" and j + 1 < len(words):
                    value = words[j + 1]
                elif w.startswith("--visibility="):
                    value = w.split("=", 1)[1]
                if value is not None and value.lower() == "public":
                    return "gh repo edit --visibility public は禁止（public化はユーザーが行う。共通AGENTS.md §3）。"
        return None
    if words[1] != "api":
        return None
    method = "GET"
    fields: list[str] = []
    uses_input = False
    endpoint = None
    j = 2
    while j < len(words):
        w = words[j]
        if w in ("-X", "--method") and j + 1 < len(words):
            method = words[j + 1].upper()
            j += 2
            continue
        if w.startswith("--method="):
            method = w.split("=", 1)[1].upper()
        elif w in ("-f", "-F", "--field", "--raw-field") and j + 1 < len(words):
            fields.append(words[j + 1])
            j += 2
            continue
        elif w.startswith(("--field=", "--raw-field=")):
            fields.append(w.split("=", 1)[1])
        elif w == "--input":
            uses_input = True
            j += 1
        elif w.startswith("--input="):
            uses_input = True
        elif not w.startswith("-") and endpoint is None:
            endpoint = w
        j += 1
    if method not in WRITE_METHODS:
        return None
    for f in fields:
        key, _, value = f.partition("=")
        if key == "visibility" and value.lower() == "public":
            return "gh api で visibility=public を書くのは禁止（public化はユーザーが行う。共通AGENTS.md §3）。"
        if key == "private" and value.lower() == "false":
            return "gh api で private=false を書くのは禁止（public化はユーザーが行う。共通AGENTS.md §3）。"
    if uses_input and endpoint and REPO_UPDATE_ENDPOINT.match(endpoint):
        return ("gh api --input で repository の設定を書き換えるのは禁止（本文を検査できないため。"
                "公開範囲の変更はユーザーが行う。共通AGENTS.md §3）。")
    return None


def check_git(words: list[str], current: str | None) -> str | None:
    directory, rest = git_effective_dir(words, current)
    if not rest:
        return None
    sub = rest[0]
    if sub == "remote":
        k = 1
        while k < len(rest) and rest[k].startswith("-"):
            k += 1
        if k < len(rest) and rest[k] == "add" and not has_remote(directory):
            return ("remoteの無いrepositoryへの git remote add は禁止"
                    "（remoteの登録と初回pushはユーザーが行う。共通AGENTS.md §3）。")
        return None
    if sub == "push":
        args = [w for w in rest[1:] if not w.startswith("-")]
        if any(URL_LIKE.match(a) for a in args):
            return ("URLを直接指定する git push は禁止（remoteの無いrepositoryの初回pushに当たる。"
                    "共通AGENTS.md §3）。")
        if not has_remote(directory):
            return ("remoteの無いrepositoryからの git push は禁止（初回pushはユーザーが行う。"
                    "共通AGENTS.md §3）。")
    return None


def check_remote_create(words: list[str], current: str | None) -> str | None:
    """1区間の語列を見て、§3 に当たれば理由を返す。"""
    words = strip_env_assignments(words)
    if not words:
        return None
    head = words[0]
    if head == "gh":
        return check_gh(words)
    if head == "git":
        return check_git(words, current)
    if head in INTERPRETERS:
        # 別のshellへ渡した文字列は実行位置。中身を語に分け直して見る
        for w in words[1:]:
            inner = check_remote_create(split_words(w), current)
            if inner:
                return inner
    return None


def remote_create_violations(command: str, cwd: str) -> list[str]:
    violations: list[str] = []
    current: str | None = cwd if os.path.isdir(cwd) else None
    for segment in SEGMENT_SPLIT.split(command):
        words = strip_env_assignments(split_words(segment))
        if not words:
            continue
        if words[0] in ("cd", "pushd"):
            current = resolve_dir(current, words[1]) if len(words) > 1 else None
            continue
        message = check_remote_create(words, current)
        if message:
            violations.append(message)
    return violations


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
    violations = remote_create_violations(command, cwd)
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
