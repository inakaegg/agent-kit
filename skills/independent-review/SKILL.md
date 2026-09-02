---
name: independent-review
description: >-
  Use for fresh-context review of non-trivial changes before a PR. Targets: user-visible behavior /
  public API / persistence / concurrency・async / security / billing / deployment / migration.
  Japanese cues: 「独立レビュー」「別contextでレビュー」「仕様レビュー」「実装計画レビュー」「実装レビュー」（旧称: gateレビュー・計画レビュー）.
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

- **重リスク作業**（公開API、永続化、並行・非同期、認証・security、課金、migration、deploy、広いarchitecture）：仕様レビュー → 実装計画レビュー → 実装レビュー。仕様と実装計画が1つの短い文書に収まる場合は、仕様と計画のレビューを1回へ統合してよい。
- **通常対象作業**（それ以外のユーザー可視動作、PR化する非自明な変更）：実装レビューのみ。仕様・計画はreviewなしで現在taskの `TASK.md` とactive planへ記録する。

reviewerのモデルとreasoning effort：

- 担当にできるモデルは agent-settings のキーが決める（重リスク作業 `REVIEW_MODEL_HEAVY`・通常対象作業 `REVIEW_MODEL_DEFAULT`・読みやすさ `REVIEW_MODEL_READABILITY`。書式は `docs/policies/review.md`）。その範囲内で実装担当と別のモデルを優先し、モデル独立性とコストの両立を図る。
- 設定値が「系統(思考量)」の形で思考量を指定している場合は、その思考量を正本として使う。
- 設定値に思考量の指定がない場合の既定：仕様・実装計画レビューは中位、実装レビューは中位を既定とし重リスク作業だけ高位へ上げる。reviewは検査であり生成ではないため、指定がない限り実装と同じ最高設定にしない。

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
- 実行した検査と読んだだけの観点を分けて書き、読んだだけの観点を「問題なし」の根拠にしない
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

**Reviewerが検査できる状態で起動する。** 実行できないまま読み合わせだけで出た判定は、走らせないと出ない競合、主張を確かめていない試験、本番の配線を留めていない試験を見逃す。起動時に次を確かめる。

- **検査コマンドの許可を明示する。** claudeの `--permission-mode acceptEdits` は編集を自動承認するだけで、Bashは承認しない。非対話（`-p`）では確認を出せないため、Reviewerのコマンドが黙って落ち、本人は「承認が下りなかった」としか報告できない。`--permission-mode default` に、当たりを絞った `--allowedTools "Bash(<検査コマンド>:*)"` を組み合わせる。編集系は `--disallowedTools` で落とす。
- **副作用の隔離は親プロセスの環境で行う。** 「使い捨て先を使ってください」とプロンプトで頼むだけだと、Reviewerが忘れれば利用者の実設定を書き換える。設定の置き場所を指す環境変数（`XDG_CONFIG_HOME` 等）は、Reviewerを起動する時点で使い捨て先へ向ける。
- **ビルド生成物の置き場所を分ける。** 実装者のworktreeでビルドすると、その `.build` のlockを握って実装者の作業を止める。`swift` なら `--scratch-path` を使い捨て先へ向ける。

Reviewerが検査を回せなかった場合は、**判定と併せてその事実を報告する**。実行の裏取りは実装者の数字によることになるため、取り込みの判断が変わる。

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
