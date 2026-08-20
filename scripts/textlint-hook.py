#!/usr/bin/env python3
"""Claude Code PostToolUse hook: .mdの編集直後にtextlintを実行する。

指摘があればexit 2でstderrへ出し、エージェントに即時修正させる。
編集のたびに走るのは決定論的で安価なlintだけ、という設計の範囲内で使う
（LLMによる意味レビューは公開・提出前のgateに置き、ここでは行わない）。

登録方法はREADMEのGit hooks節の次の項を参照。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_NAMES = (".textlintrc", ".textlintrc.json", ".textlintrc.yml", ".textlintrc.yaml")
# エージェント専用の内部文書・一時置き場は対象外（人間向け文書だけを見る）
SKIP_DIR_NAMES = {"_ai", "scratchpad", "tmp", "node_modules"}
MAX_OUTPUT_CHARS = 3000


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


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path.endswith(".md"):
        return 0
    path = Path(file_path)
    if not path.is_file():
        return 0
    if SKIP_DIR_NAMES.intersection(path.parts):
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
        "（自動修正可能な指摘は textlint --fix でも直せます）。\n" + output,
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
