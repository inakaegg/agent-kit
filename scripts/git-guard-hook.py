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

このhookはshellの完全な構文解析器ではない。決められない値（変数展開・副shell・本文を
読めない入力）は「安全と証明できない」として遮断する側に倒す。
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
# 文字列の検索ではなく、コマンド区間（&& || ; | & 改行で区切った1つ）を shell の語に分けてから、
# 先頭の語（と `cd` で移る実効directory）を見る。引用符の中や heredoc の本文に同じ文字列が
# あっても、実行位置に無ければ遮断しない。ただし文字列や heredoc を別のshellへ渡して実行する形
# （bash -c, eval, bash <<EOF, xargs 等）は中身を実行位置とみなす。

# `&&` `||` `;` `|` 改行、および単独の `&`（`2>&1` `&>` `>&` の `&` は除く）
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]|(?<![>&<|])&(?![&>])")
# 文字列をshellとして実行するもの: 引数の文字列の中身を検査する
SHELL_INTERPRETERS = {"bash", "sh", "zsh", "fish", "dash", "ksh", "eval"}
# 後続のargvをそのまま1つのコマンドとして実行するもの: option と代入を除いた残りを検査する
COMMAND_WRAPPERS = {"env", "exec", "nohup", "time", "xargs", "sudo", "doas", "command", "builtin",
                    "nice", "ionice", "caffeinate", "timeout", "gtimeout", "stdbuf", "script"}
# 別の言語の文字列実行。中身の解析はしないので、保護対象の語が入っていれば厳しい側に倒す
FOREIGN_INTERPRETERS = {"python", "python3", "node", "perl", "ruby", "osascript"}
FOREIGN_SUSPECT = re.compile(r"\bgh\s+(?:repo|api)\b|\bgit\s+(?:push|remote|config)\b")
UNSAFE_VALUE = re.compile(r"[$`]")
REPO_UPDATE_ENDPOINT = re.compile(r"^/?repos/[^/\s]+/[^/\s]+/?$")
REPO_CREATE_ENDPOINT = re.compile(
    r"^/?(?:user/repos|users/[^/\s]+/repos|orgs/[^/\s]+/repos"
    r"|repos/[^/\s]+/[^/\s]+/(?:forks|generate))/?$"
)
WRITE_METHODS = {"PATCH", "POST", "PUT", "DELETE"}
GH_API_VALUE_OPTIONS = {"-X", "--method", "-f", "-F", "--field", "--raw-field", "-H", "--header",
                        "--hostname", "-q", "--jq", "-t", "--template", "--cache", "-p", "--preview",
                        "--input"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\2(?=\n|$)", re.S)


def normalize(command: str) -> str:
    """継続行を1行にし、heredoc を処理する。

    heredoc の本文は普通はデータなので落とす。ただし本文を shell が実行する形
    （`bash <<'EOF'` など、その行の先頭コマンドが shell）では、本文を実行区間として残す。
    """
    command = re.sub(r"\\\r?\n", " ", command)

    def replace(match: re.Match) -> str:
        start = command.rfind("\n", 0, match.start()) + 1
        head_words = strip_env_assignments(split_words(command[start:match.start()]))
        if head_words and head_words[0] in SHELL_INTERPRETERS:
            return "\n" + match.group(3) + "\n"
        return " "

    return HEREDOC.sub(replace, command)


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
    """`git -C <dir>` / `--git-dir` 等のglobal optionを読み、実効directoryとsubcommand以降の語を返す。"""
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
        elif w in ("--git-dir", "--work-tree") and i + 1 < len(words):
            directory = repo_dir_from_git_dir(directory, words[i + 1], w)
            i += 2
        elif w.startswith(("--git-dir=", "--work-tree=")):
            name, _, value = w.partition("=")
            directory = repo_dir_from_git_dir(directory, value, name)
            i += 1
        elif w in ("-c", "--namespace", "--exec-path") and i + 1 < len(words):
            i += 2
        elif w.startswith("-"):
            i += 1
        else:
            break
    return directory, words[i:]


def repo_dir_from_git_dir(base: str | None, value: str, option: str) -> str | None:
    resolved = resolve_dir(base, value)
    if resolved is None:
        return None
    if option == "--work-tree":
        return resolved
    # `--git-dir x/.git` は x のrepository。それ以外の形（bare 等）は判定不能として厳しい側へ
    if os.path.basename(resolved) == ".git":
        return os.path.dirname(resolved)
    return None


def check_gh(words: list[str]) -> str | None:
    if len(words) < 2 or "--help" in words or "-h" in words:
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
                if value is None:
                    continue
                if value.lower() == "public" or UNSAFE_VALUE.search(value):
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
        if w.startswith("-X") and len(w) > 2:
            method = w[2:].upper()
        elif w.startswith("--method="):
            method = w.split("=", 1)[1].upper()
        elif w in ("-f", "-F", "--field", "--raw-field") and j + 1 < len(words):
            fields.append(words[j + 1])
            j += 2
            continue
        elif w.startswith(("--field=", "--raw-field=")):
            fields.append(w.split("=", 1)[1])
        elif w.startswith(("-f", "-F")) and len(w) > 2 and not w.startswith("--"):
            fields.append(w[2:])
        elif w == "--input":
            uses_input = True
            j += 1
        elif w.startswith("--input="):
            uses_input = True
        elif w in GH_API_VALUE_OPTIONS and j + 1 < len(words):
            j += 2
            continue
        elif w.startswith("-"):
            pass
        elif endpoint is None:
            endpoint = w
        j += 1
    # field を付けて method を省くと gh api は POST で送る（gh api --help）
    if fields and method == "GET" and not any(w in ("-X", "--method") or w.startswith(("-X", "--method=")) for w in words):
        method = "POST"
    if method not in WRITE_METHODS:
        return None
    if endpoint and REPO_CREATE_ENDPOINT.match(endpoint):
        return "gh api で repository を作る endpoint への書き込みは禁止（remote repositoryの作成はユーザーが行う。共通AGENTS.md §3）。"
    if endpoint is None and uses_input:
        return "gh api の endpoint を決められない --input 付きの書き込みは禁止（本文を検査できないため。共通AGENTS.md §3）。"
    for f in fields:
        key, _, value = f.partition("=")
        if key not in ("visibility", "private"):
            continue
        if value.startswith("@") or UNSAFE_VALUE.search(value):
            return f"gh api で {key} をファイルや展開で渡すのは禁止（値を検査できないため。共通AGENTS.md §3）。"
        if key == "visibility" and value.lower() == "public":
            return "gh api で visibility=public を書くのは禁止（public化はユーザーが行う。共通AGENTS.md §3）。"
        if key == "private" and value.lower() == "false":
            return "gh api で private=false を書くのは禁止（public化はユーザーが行う。共通AGENTS.md §3）。"
    if uses_input and endpoint and REPO_UPDATE_ENDPOINT.match(endpoint):
        return ("gh api --input で repository の設定を書き換えるのは禁止（本文を検査できないため。"
                "公開範囲の変更はユーザーが行う。共通AGENTS.md §3）。")
    return None


def is_repository_url(arg: str) -> bool:
    """git push の1つ目の引数が、名前付きremoteではなく repository の場所そのものか。"""
    if "://" in arg or arg.startswith(("/", "./", "../", "~")):
        return True
    # scp-style `host:path` / `user@host:path`（refspec の `a:b` は1つ目の引数には来ない）
    return ":" in arg


def check_git(words: list[str], current: str | None) -> str | None:
    if "--help" in words or "-h" in words:
        return None
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
    if sub == "config":
        keys = [w for w in rest[1:] if re.match(r"^remote\.[^.]+\.(?:url|pushurl)$", w, re.I)]
        if keys and not has_remote(directory):
            return ("remoteの無いrepositoryへ git config で remote.*.url を書くのは禁止"
                    "（remoteの登録と初回pushはユーザーが行う。共通AGENTS.md §3）。")
        return None
    if sub == "push":
        options = rest[1:]
        if any(w in ("-n", "--dry-run") for w in options):
            return None
        args: list[str] = []
        k = 0
        while k < len(options):
            w = options[k]
            if w in ("--repo",) and k + 1 < len(options):
                # --repo <url> は repository の指定そのもの
                args.insert(0, options[k + 1])
                k += 2
                continue
            if w.startswith("--repo="):
                args.insert(0, w.split("=", 1)[1])
                k += 1
                continue
            if w in ("-o", "--push-option", "--receive-pack", "--exec") and k + 1 < len(options):
                k += 2
                continue
            if w.startswith("-o") and len(w) > 2 and not w.startswith("--"):
                k += 1
                continue
            if not w.startswith("-"):
                args.append(w)
            k += 1
        if args and (UNSAFE_VALUE.search(args[0]) or is_repository_url(args[0])):
            return ("URLや展開される値を直接指定する git push は禁止（remoteの無いrepositoryの初回pushに当たる。"
                    "共通AGENTS.md §3）。")
        if not has_remote(directory):
            return ("remoteの無いrepositoryからの git push は禁止（初回pushはユーザーが行う。"
                    "共通AGENTS.md §3）。")
    return None


def strip_wrapper(words: list[str]) -> list[str]:
    """env / exec / nohup 等を剥がし、実際に実行されるargvを返す。"""
    rest = words[1:]
    while rest and (rest[0].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", rest[0])):
        # timeout <秒> のように値を1つ取る形は、数字の語も読み飛ばす
        rest = rest[1:]
    while rest and re.match(r"^\d+(?:\.\d+)?[smhd]?$", rest[0]):
        rest = rest[1:]
    return rest


def check_remote_create(words: list[str], current: str | None, depth: int = 0) -> str | None:
    """1区間の語列を見て、§3 に当たれば理由を返す。"""
    words = strip_env_assignments(words)
    if not words or depth > 5:
        return None
    head = os.path.basename(words[0])
    if head == "gh":
        return check_gh(words)
    if head == "git":
        return check_git(words, current)
    if head in COMMAND_WRAPPERS:
        return check_remote_create(strip_wrapper(words), current, depth + 1)
    if head in SHELL_INTERPRETERS:
        # 別のshellへ渡した文字列は実行位置。中身を区間に分け直して見る
        for w in words[1:]:
            for segment in SEGMENT_SPLIT.split(w):
                inner = check_remote_create(split_words(segment), current, depth + 1)
                if inner:
                    return inner
        return None
    if head in FOREIGN_INTERPRETERS:
        for w in words[1:]:
            if FOREIGN_SUSPECT.search(w):
                return ("別の言語の文字列に gh repo / gh api / git push 等が含まれている（中身を検査できないため遮断。"
                        "共通AGENTS.md §3）。")
    return None


def substitutions(command: str) -> list[str]:
    """`$( … )` と backtick の中身。shell はこれらも実行する。入れ子は再帰で拾う。"""
    found: list[str] = []
    i = 0
    while i < len(command):
        if command.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(command) and depth:
                if command.startswith("$(", j):
                    depth += 1
                    j += 2
                    continue
                if command[j] == "(":
                    depth += 1
                elif command[j] == ")":
                    depth -= 1
                j += 1
            inner = command[i + 2:j - 1] if depth == 0 else command[i + 2:]
            found.append(inner)
            found.extend(substitutions(inner))
            i = j
            continue
        if command[i] == "`":
            j = command.find("`", i + 1)
            if j < 0:
                found.append(command[i + 1:])
                break
            found.append(command[i + 1:j])
            i = j + 1
            continue
        i += 1
    return found


def remote_create_violations(command: str, cwd: str, depth: int = 0) -> list[str]:
    violations: list[str] = []
    current: str | None = cwd if os.path.isdir(cwd) else None
    if depth < 5:
        for inner in substitutions(command):
            violations.extend(remote_create_violations(inner, cwd, depth + 1))
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
