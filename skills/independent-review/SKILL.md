---
name: independent-review
description: >-
  Use for fresh-context review of non-trivial changes before a PR. Targets: user-visible behavior /
  public API / persistence / concurrency・async / security / billing / deployment / migration.
  Japanese cues: 「独立レビュー」「別contextでレビュー」「仕様レビュー」「計画レビュー」「実装レビュー」（旧称: gateレビュー）.
---

# Independent Review

## 使用条件

- PRへ出す非自明な変更
- user-visible behavior、public API、persistence、concurrency、async state
- auth、security、privacy、billing、deployment、migration
- architecture boundaryまたは広いrefactor
- 実装者が設計判断へ強くanchoringしている可能性がある

小さなdocs typo、formatterだけの変更等は省略できる。

## 0. レビュー段階の適用範囲とreviewer設定

共通AGENTS §7の区分に従う。

- **重リスク作業**（公開API、永続化、並行・非同期、認証・security、課金、migration、deploy、広いarchitecture）：仕様レビュー → 計画レビュー → 実装レビュー。仕様と実装計画が1つの短い文書に収まる場合は、仕様と計画のレビューを1回へ統合してよい。
- **通常対象作業**（それ以外のユーザー可視動作、PR化する非自明な変更）：実装レビューのみ。仕様・計画はreviewなしで現在taskの `TASK.md` とactive planへ記録する。

reviewerのreasoning effort既定：

- reviewは検査であり生成ではない。実装と同じ最高設定（例：xhigh）を既定にしない。
- 仕様・計画レビュー：中位（例：codex `medium`、claude標準effort）。
- 実装レビュー：中位を既定とし、重リスク作業だけ高位（`high` 以上）へ上げる。
- 実装をCodexが行った場合はreviewerへClaudeを、Claudeが行った場合はCodexを優先し、モデル独立性とコストの両立を図る。

## 1. 独立性

- 履歴を共有しない別セッションを使う。
- 可能なら実装とは別のtool/modelを使う。
- 実装者の会話履歴、途中仮説、自己評価、期待する結論を渡さない。
- Reviewer processでは、実装者向けの作業手順注入（SessionStart hook、skill案内、plugin指示）を無効化する。プロジェクト規約 `AGENTS.md` は §2 の通り渡すが、実装者の作業手順は渡さない。
  - claude: `--setting-sources ""` `--disable-slash-commands` `--no-session-persistence`
  - codex: `--ignore-user-config` `--ephemeral` `-s read-only`
- Reviewerはcodeを変更しないread-only roleとする。
- サブエージェントを無制限に使わない。別CLI processを1つ、最大1reviewerとする。

## 2. Reviewerへ渡す資料

Reviewerへ渡すもの：

- 適用される `AGENTS.md`
- `_ai/TASK.md` または要件summary
- 関連SPEC・ADR
- 同じ機能を扱う既存の設計文書・referent table（仕様がこれらと矛盾する場合、矛盾の明示があるかを見る）
- intended baseとheadの完全diff
- test/verificationの実結果
- screenshot、metric、log等の必要な資料

渡さないもの：

- 「この実装は正しいはず」等の誘導
- rejectしてほしい/採用してほしい案
- 実装者の弁明
- unrelated chat history

情報が多い場合は現在taskの `reviews/handoff.md` を作り、事実とpathだけを書く。

## 3. Reviewer contract

このSkill内の `assets/REVIEW_PROMPT.md` を使う。要点：

- confirmedなcorrectness、requirement violation、security/privacy、data loss、compatibilityだけ
- 渡された既存設計文書との未申告の矛盾と、`[エージェント判断]` ラベルの妥当性を細部より先に確認する
- 具体的なinput、state、code path、locationを必須にする
- style、naming、好みのrefactor、根拠のない懸念を報告しない
- 重大度順に最大5件。修正必須の指摘は最大2件とし、残りは記録のみの指摘とする
- 仕様レビューでは実装手段・test構成・CIの細部を修正必須にしない
- 最後にmachine-readable verdict

missing testは、taskの合格条件違反、またはbehaviorを検証不能にする場合だけ修正必須とする。

## 4. Reviewerの検証

Reviewerは可能な範囲で：

1. task/specからexpected behaviorを再構成
2. diffだけでなく周辺codeとcall siteを確認
3. targeted search、type check、cheap test、成果物の確認
4. failure pathを具体化
5. implementer claimをcode/evidenceで照合

`VERDICT`行がない、途中でtool failure、対象diffが違う場合はreview未完了とする。

## 5. 指摘の仕分け

各指摘を次へ分類する。

- **FIX**：再現またはcode pathで確認した修正必須の問題
- **RECORD**：妥当だが現在taskでは直さない。条件とriskを記録
- **REFUTE**：誤検知、outdated、spec誤読。反証を1行残す
- **BLOCKED**：環境・credential・product decision不足で判定不能

bot/modelのsuggestionをそのままpatchしない。影響範囲、同型call site、side effectを確認する。

## 6. 反復

```text
review N回目（1回目はfull diff、以降は修正差分と関連周辺）
→ 指摘を仕分け
→ FIXだけ修正
→ 対象検査＋全体検査
→ 履歴を共有しない別セッションで次の回
→ LGTMまたは停止条件で終了
```

- 回数として数えるのは、必要な資料を読めて `VERDICT` 行まで出した完了reviewだけ。§4の未完了review（tool failure、`VERDICT` 欠落、対象diff違い）は数えず、原因を直して再実行する。
- `VERDICT: LGTM` が出たら即終了する。
- 2回までを既定とする。2回目は前回の修正必須の解消と修正差分の確認を主対象とし、新たに出た指摘はsecurity・データ消失・互換性破壊を除き修正必須とせずRECORDへ置く。
- 2回目の終了時にLGTMでない場合：security・データ消失・互換性破壊の修正必須が残るなら人間判断へ戻す。それ以外の残指摘だけならRECORDへ記録し通過とする。完了報告へ残指摘を明記する。
- 回数を追加できるのは、重大3種の修正必須を修正した後の解消確認1回だけとする。
- 同じ修正必須の指摘が新しい証拠なく反復する場合は、回数を重ねず人間判断へ戻す。
- 各回は§1の独立性と§3のreviewer contract（最大5件）をそのまま満たす。回数を増やす代わりにこれらを緩めない。
- この上限はPRのbot・CI反復（`$pr-review-loop` の最大5iteration）とは別に数える。
- 同型の指摘が2件以上なら、対応表を作って監査し、mechanical checkを追加する。

## 7. stateと報告

現在taskのdirectory配下 `_ai/tasks/<開始日-slug>/reviews/` に次を保存できる。

- `handoff.md`（引き継ぎ）
- `round-<N>.md`（N回目の指摘）
- `triage-<N>.md`（N回目の仕分け）
- `verification.md`

最終報告：

- reviewer tool/model category
- base/head
- verdict
- 実施回数と終了理由（LGTM / 非改善 / 反復 / 回数上限）
- FIX / RECORD / REFUTE件数
- 修正後に再実行した検査
- 未確認範囲
