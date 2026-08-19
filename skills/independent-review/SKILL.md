---
name: independent-review
description: Use when PR前の非自明な変更、user-visible behavior、public API、永続化、並行・非同期、security、billing、deployment、またはmigrationをfresh contextでreviewするとき。
---

# Independent Review

## 使用条件

- PRへ出す非自明な変更
- user-visible behavior、public API、persistence、concurrency、async state
- auth、security、privacy、billing、deployment、migration
- architecture boundaryまたは広いrefactor
- 実装者が設計判断へ強くanchoringしている可能性がある

小さなdocs typo、formatterだけの変更等は省略できる。

## 0. gateの適用範囲とreviewer設定

共通AGENTS §7の区分に従う。

- **重リスク作業**（公開API、永続化、並行・非同期、認証・security、課金、migration、deploy、広いarchitecture）：gate 1（仕様）→ gate 2（計画）→ gate 3（実装）。仕様と実装計画が1つの短い文書に収まる場合は、gate 1と2を1回のreviewへ統合してよい。
- **通常対象作業**（それ以外のユーザー可視動作、PR化する非自明な変更）：gate 3のみ。仕様・計画はreviewなしで `_ai/TASK.md` とactive planへ記録する。

reviewerのreasoning effort既定：

- reviewは検査であり生成ではない。実装と同じ最高設定（例：xhigh）を既定にしない。
- gate 1・2：中位（例：codex `medium`、claude標準effort）。
- gate 3：中位を既定とし、重リスク作業だけ高位（`high` 以上）へ上げる。
- 実装をCodexが行った場合はreviewerへClaudeを、Claudeが行った場合はCodexを優先し、モデル独立性とコストの両立を図る。

## 1. 独立性

- fresh session/contextを使う。
- 可能なら実装とは別のtool/modelを使う。
- 実装者の会話履歴、途中仮説、自己評価、期待する結論を渡さない。
- Reviewer processでは、実装者向けの作業手順注入（SessionStart hook、skill案内、plugin指示）を無効化する。プロジェクト規約 `AGENTS.md` は §2 の通り渡すが、実装者の作業手順は渡さない。
  - claude: `--setting-sources ""` `--disable-slash-commands` `--no-session-persistence`
  - codex: `--ignore-user-config` `--ephemeral` `-s read-only`
- Reviewerはcodeを変更しないread-only roleとする。
- サブエージェントを無制限に使わない。別CLI processを1つ、最大1reviewerとする。

## 2. 入力artifact

Reviewerへ渡すもの：

- 適用される `AGENTS.md`
- `_ai/TASK.md` または要件summary
- 関連SPEC・ADR
- 同じ機能を扱う既存の設計文書・referent table（仕様がこれらと矛盾する場合、矛盾の明示があるかを見る）
- intended baseとheadの完全diff
- test/verificationの実結果
- screenshot、metric、log等の必要artifact

渡さないもの：

- 「この実装は正しいはず」等の誘導
- rejectしてほしい/採用してほしい案
- 実装者の弁明
- unrelated chat history

情報が多い場合は `_ai/review-handoff.md` を作り、事実とpathだけを書く。

## 3. Reviewer contract

このSkill内の `assets/REVIEW_PROMPT.md` を使う。要点：

- confirmedなcorrectness、requirement violation、security/privacy、data loss、compatibilityだけ
- 渡された既存設計文書との未申告の矛盾と、`[エージェント判断]` ラベルの妥当性を細部より先に確認する
- 具体的なinput、state、code path、locationを必須にする
- style、naming、好みのrefactor、根拠のない懸念を報告しない
- 重大度順に最大5件。blockingは最大2件とし、残りは非blockingとして記録する
- gate 1では実装手段・test構成・CIの細部をblockingにしない
- 最後にmachine-readable verdict

missing testは、taskのacceptance違反、またはbehaviorを検証不能にする場合だけblockingとする。

## 4. Reviewerの検証

Reviewerは可能な範囲で：

1. task/specからexpected behaviorを再構成
2. diffだけでなく周辺codeとcall siteを確認
3. targeted search、type check、cheap test、artifact確認
4. failure pathを具体化
5. implementer claimをcode/evidenceで照合

`VERDICT`行がない、途中でtool failure、対象diffが違う場合はreview未完了とする。

## 5. triage

各findingを次へ分類する。

- **FIX**：再現またはcode pathで確認したblocking issue
- **RECORD**：妥当だが現在taskのblockingではない。条件とriskを記録
- **REFUTE**：誤検知、outdated、spec誤読。反証を1行残す
- **BLOCKED**：環境・credential・product decision不足で判定不能

bot/modelのsuggestionをそのままpatchしない。blast radius、同型call site、side effectを確認する。

## 6. 反復

```text
review round N（round 1はfull diff、以降は修正差分と関連周辺）
→ triage
→ FIXだけ修正
→ targeted + full gate
→ fresh contextで次round
→ LGTMまたは停止条件で終了
```

- roundとして数えるのは、必要artifactを読めて `VERDICT` 行まで出した完了reviewだけ。§4の未完了review（tool failure、`VERDICT` 欠落、対象diff違い）は数えず、原因を直して再実行する。
- `VERDICT: LGTM` が出たら即終了する。
- round 2までを既定とする。round 2は前roundのblocking解消と修正差分の確認を主対象とし、新たに出た指摘はsecurity・data loss・互換性破壊を除きblockingとせずRECORDへ置く。
- round 2終了時にLGTMでない場合：security・data loss・互換性破壊のblockingが残るなら人間判断へ戻す。それ以外の残指摘だけならRECORDへ記録しgate通過とする。完了報告へ残指摘を明記する。
- roundを追加できるのは、重大3種のblockingを修正した後の解消確認1回だけとする。
- 同じblocking findingが新しい証拠なく反復する場合は、roundを重ねず人間判断へ戻す。
- 各roundは§1のfresh context・独立性と§3のreviewer contract（最大5件）をそのまま満たす。round数を増やす代わりにこれらを緩めない。
- この上限はPRのbot・CI反復（`$pr-review-loop` の最大5iteration）とは別に数える。
- 同型findingが2件以上なら、横断で監査し、mechanical checkを追加する。

## 7. stateと報告

`_ai/reviews/<task-id>/` に次を保存できる。

- `handoff.md`
- `round-<N>.md`
- `triage-<N>.md`
- `verification.md`

最終報告：

- reviewer tool/model category
- base/head
- verdict
- 実施round数と終了理由（LGTM / 非改善 / 反復 / round上限）
- FIX / RECORD / REFUTE件数
- 修正後に再実行したgate
- 未確認範囲
