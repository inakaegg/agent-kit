# TASK — <短いtask名>

> このfileは現在taskの契約である。共通ルールや作業履歴は書かない。
> Agentは、合格条件を都合よく緩めたり、scopeを無断で変えたりしてはならない。
> 記入前に、要件の曖昧点・複数解釈は推測で埋めず、重要な順に1問ずつユーザーへ確認する。
> 目的に不要な機能・汎用化は範囲外へ移し（YAGNI）、合意した内容だけを本fileへ確定する。

## Status

- Branch: <task branch名>
- 期間: <開始日> 〜 <終了日または進行中>
- 結果: 未完 | 完了 | 中止 | 引き継ぎ先: <slug>
- 状態: Ready | In progress | Blocked | Done

## Goal / user value

<利用者・製品・運用に何が改善するかを一文で書く>

## User requirements

- [ユーザー指示] ...

## Confirmed facts

- [確認方法・対象・件数] ...

## Assumptions to verify

- [未確認] ...
  - 確認せず進める理由:
  - 外れた場合の影響:

## Problem / current behavior

- 入力・操作:
- 現在の結果:
- 期待結果:
- 再現・evidence:

## Scope

- ...

## Out of scope

- ...

## Acceptance criteria

1. ...
2. ...
3. 必要なproject quality gateが成功する
4. 必要なfresh-context reviewにblocking findingがない

## Verification and evidence

| acceptance | command / procedure | artifact / metric |
|---|---|---|
| 1 | ... | ... |

## Compatibility / risk

- public API:
- data/schema:
- security/privacy:
- performance/cost:
- rollback:

## External effects and permission

- remote write:
- paid API/GPU/download:
- visibility change:
- destructive operation:
- 必要な明示確認:

## Stop / escalate

- 最大attempt/iteration:
- 非改善条件:
- cost/resource上限:
- 人間判断が必要になる条件:

## Linked sources of truth

- Specification:
- Architecture / ADR:
- Active plan: `_ai/active-plan.md`
- Verification:
