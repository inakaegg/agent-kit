#!/usr/bin/env bash
# agent-kit自身の検証。pre-push（git-hooks/pre-push）とCI（.github/workflows/ci.yml）から呼ぶ。
# fast と full は同じ（どちらも数秒で終わる）。
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/validate-kit.py
python3 -m unittest discover -s tests
