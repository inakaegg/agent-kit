# Verification and quality gates

## Canonical commands

| Gate | Command | Required when |
|---|---|---|
| Format check | `<FORMAT_CHECK_COMMAND>` | source/test change |
| Lint/static analysis | `<LINT_COMMAND>` | source/test change |
| Type/build | `<TYPECHECK_OR_BUILD_COMMAND>` | compiled/typed code |
| Targeted tests | `<TARGETED_TEST_COMMAND>` | edit loop |
| Unit suite | `<UNIT_TEST_COMMAND>` | behavior change |
| Integration | `<INTEGRATION_TEST_COMMAND>` | boundary/storage/API |
| UI/E2E | `<E2E_COMMAND>` | user-visible workflow |
| Full gate | `<FULL_CHECK_COMMAND>` | before completion |

placeholderは実在commandへ置換する。clean checkoutで再現できないcommandは、前提をrunbookへ記載するまでcanonicalにしない。

## Change-to-evidence matrix

| Change | Additional evidence |
|---|---|
| Bug fix | old behaviorを示すregression test |
| Public API | compatibility testまたはbreaking approval |
| Data/schema | migration、restore/rollback、data test |
| UI | actual render、screenshot/recording、interaction |
| Audio/media/AI | fixed fixtures、objective metrics、representative output |
| Performance | baseline、after、environment、method |
| Security/auth | threat-focused tests、independent review |
| Dependency | reason、license/security、lockfile、rollback |

## Evidence format

```text
Command: <exact command>
Result: PASS | FAIL | NOT RUN
Exit code: <number if available>
Artifact/output: <path or concise excerpt>
Notes: <pre-existing failure / environment limit / none>
```

## Baseline failures

- 変更前から存在するfailureを記録する。
- 根拠なく「今回と無関係」と分類しない。
- 許可なくscopeを広げて修正しない。
- 比較不能なら停止して報告する。

## Manual verification

手動確認はmechanical checksを補完し、置き換えない。procedure、input、expected、observed、artifactを残す。「問題なさそう」だけで完了しない。
