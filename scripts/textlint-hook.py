#!/usr/bin/env python3
"""Claude Code / Codex の PostToolUse hook: .mdの編集直後にtextlintを実行する。

指摘があればexit 2でstderrへ出し、エージェントに即時修正させる。
編集のたびに走るのは決定論的で安価なlintだけ、という設計の範囲内で使う
（LLMによる意味レビューは公開・提出前のgateに置き、ここでは行わない）。

入力はstdinのJSON。編集されたファイルの取り方はCLIで異なる。
  - Claude Code（Edit / Write）: tool_input.file_path
  - Codex（apply_patch）: tool_input.command に patch 本文が入るので、
    "*** Add File:" / "*** Update File:"（"*** Move to:" があれば移動先）の行から取る。
    相対pathは payload の cwd 基準で解決する。

登録方法はREADMEのGit hooks節の次の項を参照。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_NAMES = (".textlintrc", ".textlintrc.json", ".textlintrc.yml", ".textlintrc.yaml")
# エージェント専用の内部文書・一時置き場は対象外（人間向け文書だけを見る）。
# .claude/.codex/.agents配下はメモリ・セッション記録などの内部文書のため除外する。
SKIP_DIR_NAMES = {"_ai", "scratchpad", "tmp", "node_modules", ".claude", ".codex", ".agents"}
MAX_OUTPUT_CHARS = 3000
# 日本語lintなので、日本語の文書だけを対象にする。「日本語の文字を1つでも含む」では、
# 英語READMEの「🇯🇵 日本語: README.ja.md」のような相互リンク1行で英文全体に日本語規則が
# かかってしまうため、日本語の文字（ひらがな・カタカナ・漢字）が英数字＋日本語文字の
# JAPANESE_RATIO_MIN 以上を占める場合だけ対象とする。
# 文字集合は git-hooks/pre-commit のperl判定と同じ範囲（ひらがな・カタカナ・々等の記号・
# CJK統合漢字＋拡張A・半角カナ）。片方だけ変えないこと（tests/test_textlint_hook.py が突合する）。
JAPANESE_RE = re.compile(
    r"[\u3005\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]"
)
LATIN_RE = re.compile(r"[A-Za-z]")
# 2%: 英語READMEの相互リンク1行（1%未満）は対象外、英語骨格に日本語の注記が数文ある
# テンプレート（4%前後）は対象に入る。
JAPANESE_RATIO_MIN = 0.02
# Codex の apply_patch 形式。Add/Update が対象ファイル、直後の Move to が移動先。
# Delete File は編集後に存在しないので対象外。
PATCH_TARGET_RE = re.compile(r"^\*\*\* (Add File|Update File): (.+)$")
PATCH_MOVE_RE = re.compile(r"^\*\*\* Move to: (.+)$")


def is_japanese_document(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    ja = len(JAPANESE_RE.findall(text))
    if ja == 0:
        return False
    latin = len(LATIN_RE.findall(text))
    return ja / (ja + latin) >= JAPANESE_RATIO_MIN


def patch_targets(patch: str) -> list[str]:
    """apply_patch の本文から、編集後に存在するファイルのpathを出現順に返す。"""
    targets: list[str] = []
    for line in patch.splitlines():
        m = PATCH_TARGET_RE.match(line)
        if m:
            targets.append(m.group(2).strip())
            continue
        m = PATCH_MOVE_RE.match(line)
        if m and targets:
            targets[-1] = m.group(1).strip()
    return targets


def edited_markdown_paths(payload: dict) -> list[Path]:
    """hook入力から、lint対象の .md の絶対pathを返す（CLIの違いをここで吸収する）。"""
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return []
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        candidates = [file_path]
    elif payload.get("tool_name") == "apply_patch":
        command = tool_input.get("command")
        candidates = patch_targets(command) if isinstance(command, str) else []
    else:
        return []
    base = Path(payload.get("cwd") or os.getcwd())
    paths: list[Path] = []
    for candidate in candidates:
        if not candidate.endswith(".md"):
            continue
        path = Path(candidate)
        if not path.is_absolute():
            path = base / path
        if path not in paths:
            paths.append(path)
    return paths


def repo_root_of(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def skip_textlint_configured(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path.parent), "config", "--type=bool",
         "--default=false", "hooks.skipTextlint"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def resolve_config(path: Path) -> Path | None:
    root = repo_root_of(path)
    if root is not None:
        for name in CONFIG_NAMES:
            candidate = root / name
            if candidate.is_file():
                return candidate
    fallback = KIT_ROOT / ".textlintrc.json"
    return fallback if fallback.is_file() else None


def lint_one(path: Path) -> int:
    """1ファイルをlintし、指摘があれば stderr へ出して 2 を返す。対象外・未導入は 0。"""
    if not path.is_file():
        return 0
    if SKIP_DIR_NAMES.intersection(path.parts):
        return 0
    if not is_japanese_document(path):
        return 0
    if shutil.which("textlint") is None:
        return 0  # 未導入環境ではpre-commit同様に黙って通す（fail-open）
    if skip_textlint_configured(path):
        return 0
    config = resolve_config(path)
    if config is None:
        return 0
    result = subprocess.run(
        ["textlint", "--no-color", "--config", str(config), str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return 0
    output = (result.stdout or result.stderr).strip()[:MAX_OUTPUT_CHARS]
    print(
        f"textlint: {path} に日本語文書lintの指摘があります。"
        "いま編集した文書なので、この場で修正してください"
        "（自動修正可能な指摘は textlint --fix でも直せます）。"
        "規則が実態に合わない場合は、共有kit側の設定を編集せず、"
        "対象リポジトリ直下の .textlintrc.json（無ければkit設定を複製して作成）で調整してください。\n"
        + output,
        file=sys.stderr,
    )
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    status = 0
    for path in edited_markdown_paths(payload):
        status = max(status, lint_one(path))
    return status


if __name__ == "__main__":
    sys.exit(main())
