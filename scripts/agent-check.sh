#!/usr/bin/env bash
# agent-kit自身の検証。pre-push（git-hooks/pre-push）とCI（.github/workflows/ci.yml）から呼ぶ。
# fast と full は同じ（どちらも数秒で終わる）。
set -euo pipefail

# pre-push hookから呼ばれると、gitがhookへ渡す GIT_DIR 等の絶対パスがこの下の
# すべての子プロセスへ継承される。テストが一時repoで練習用のgit操作をしても、
# gitはそれらを見て呼び出し元のrepoを書き換えてしまう（configの上書き、作業用branchの
# 作成、実branchへのcommit混入）。個々のテスト側の隔離漏れをここで一律に塞ぐ。
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR GIT_PREFIX GIT_ALTERNATE_OBJECT_DIRECTORIES

cd "$(dirname "$0")/.."
python3 scripts/validate-kit.py
python3 -m unittest discover -s tests
