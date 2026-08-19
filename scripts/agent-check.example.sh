#!/usr/bin/env bash

set -euo pipefail

mode="${1:-full}"

# projectへ導入するとき、placeholderを実在commandへ置換する。
fast_checks=(
  "<FORMAT_CHECK_COMMAND>"
  "<LINT_COMMAND>"
  "<TYPECHECK_OR_BUILD_COMMAND>"
  "<UNIT_TEST_COMMAND>"
)

full_only_checks=(
  "<INTEGRATION_TEST_COMMAND>"
  "<E2E_OR_ARTIFACT_VERIFICATION_COMMAND>"
)

run_check() {
  local command="$1"

  if [[ "$command" == \<*\> ]]; then
    printf 'Unconfigured check: %s\n' "$command" >&2
    exit 2
  fi

  printf '\n>>> %s\n' "$command"
  bash -lc "$command"
}

case "$mode" in
  fast)
    for command in "${fast_checks[@]}"; do
      run_check "$command"
    done
    ;;
  full)
    for command in "${fast_checks[@]}"; do
      run_check "$command"
    done
    for command in "${full_only_checks[@]}"; do
      run_check "$command"
    done
    ;;
  *)
    printf 'Usage: %s [fast|full]\n' "$0" >&2
    exit 2
    ;;
esac
