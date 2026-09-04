---
name: pr-review-loop
description: >-
  Use on an explicitly approved PR to drive convergence on the latest head: reviewer and bot findings /
  CI / fixes / re-verification / re-review. Japanese cues: 「PRレビュー対応」「botの指摘を処理」「CIを通して再review」.
---

# PR Review Loop

## 前提権限

- PRのread、comment取得、CI log取得はread-onlyとして行える。
- push、PR comment投稿、review再依頼、merge等のremote writeは、共通AGENTSと最新ユーザー指示の許可範囲に従う。
- mergeはこのSkillの完了から自動的に許可されない。

## 1. 初期状態

確認・記録する。

- repositoryとPR番号
- PR state、draft、base branch、head branch、latest head SHA
- mergeabilityとrequired checks
- project `AGENTS.md`、verification command、merge policy
- reviewer/botの種類とreview signal
- local working treeとbranch

state directory（現在のtask directory配下。共通AGENTS §2 の `_ai/` 構成に従う）：

```text
_ai/tasks/<開始日-slug>/reviews/pr-<PR番号>/
```

各iterationに、head SHA、指摘、仕分け結果、変更、checks、push/review signalをJSONまたはMarkdownで残す。

## 2. latest headのfeedbackだけを対象にする

- review、inline comment、top-level comment、CI runをすべて確認する。
- 可能ならhead SHA、reviewed commit、workflow runのhead SHAで最新性を判定する。
- timestampだけに依存しない。使う場合はiteration startとtimezoneを明示する。
- 古いcommitへのcommentは、現在codeにも該当するか再確認する。
- silence、rate limit、timeout、botのmarketing section、walkthrough summaryをapprovalまたは指摘として数えない。
- 特定bot名やworkflow名をhardcodeせず、repositoryからdiscoverする。
- projectが要求するかユーザーが依頼したbotが利用上限・障害で止まっている場合（「usage limit」等のcommentだけでreviewが無い）は、指摘ゼロと数えない。再開時刻を確認してiteration記録へ残し、再開時刻に再依頼（`@<bot> review` 等のcomment投稿。remote writeなので許可範囲に従い、無ければ記録と報告に留める）する。再開時刻が24時間以内なら待機として扱い、本Skill §7の「review signalを返さない」停止条件に当てはめない。PR作成直後で必須botがまだ何も返していない場合も同じ上限（24時間）で待ち、poll間隔は数分単位にする。24時間を超えるなら状態を記録して人間判断へ戻す。任意のbot（要求も依頼もされていないもの）の停止では待たない。待つあいだは他の作業へ戻ってよい。

## 3. 指摘の仕分け

対応が必要なすべての指摘を確認し、次へ分類する。

- **MUST-FIX**：確認済みbug、security、data loss、requirement violation、breaking regression
- **VALID-NONBLOCKING**：正しいが現在PRを止めないquality improvement
- **FALSE-POSITIVE**：code/specを誤読、outdated、再現不能
- **FOLLOW-UP**：実害や着手条件があるがscope外
- **BLOCKED**：credential、environment、product decision不足

各指摘について：

- location
- reviewer
- actual code pathまたはreproduction
- classification
- action/reason

を残す。bot同士の矛盾を両方機械的に満たそうとせず、自分でcodeとspecを判定する。

## 4. 修正iteration

修正はそのターンの許可範囲で行う。「PRを作成して」だけの許可はpushとPR作成までで、指摘への修正を含まない。修正の許可がなければ、仕分け結果を報告して止める。Draft PRでは状態の確認と記録だけ行い、修正iterationへ進まない。

1. MUST-FIXを、同型箇所の横断検索後にまとめて修正
2. 必要なregression testを追加
3. projectのtargeted checks
4. 必須検査の全体実行
5. final diff確認
6. 許可がある場合だけcommit・push
7. 新しいhead SHAを記録
8. latest headへのreview/CIを取得

unrelated CI failureも無視せず、変更前から失敗していたか・base branch・infrastructure・今回差分のどれが原因かを確認する。範囲外で自力修正不能ならBLOCKEDとして報告する。

## 5. base branchの変化

- iteration間にbaseが進んだか確認する。
- 自動merge/rebaseしてよいとは限らない。project policyとユーザー権限に従う。
- conflictなしのsyncが明示的に許可されている場合だけ実行し、sync後に必須検査を再実行する。
- semantic conflictは推測で解消しない。

## 6. 収束条件

次をすべて満たす。

- latest headに未解決MUST-FIXがない
- 対応が必要な全指摘へFIX / RECORD / REFUTE / FOLLOW-UP / BLOCKEDの判断がある
- required CIがgreen、または明示された環境blockだけが残る
- projectが要求するか、ユーザーが依頼したreview signalがlatest headに対して完了
- 履歴を共有しない別セッションのreviewにも修正必須の指摘がない（軽微変更、および `INDEPENDENT_REVIEW=false` の通常対象作業ではこの条件を要求しない。重リスク作業は常に要求する）

botのLGTMだけで自分のreviewを省略しない。逆に、false positiveを無理に修正してbot全員を満足させる必要もないが、反証を残す。

## 7. iteration上限

bot reviewの反復は最大2iteration。3巡目以降の指摘は課題として記録し、PRは収束扱いにする（正しさ・security・データ消失・互換性に関わる修正必須を除く）。bot指摘の仕分け既定（P0・P1相当だけ修正必須、P2以下は記録のみ）は `docs/policies/review.md` に従う。

次の場合は上限前でも停止する。

- 同じ指摘が理由を変えず反復
- reviewer同士が解消不能に矛盾
- 2iteration連続で新しい実質的改善がない
- CI/serviceがreview signalを返さない（queued・runningの実行中は完了まで待つ。待ちの上限は停止中botと同じ24時間で、超えたら状態を記録して人間判断へ戻す）
- scopeが元PRから大きく逸脱
- 未許可のbreaking change、migration、cost、remote operationが必要

停止時はstalemateを人間判断へ戻す。

## 8. merge前

mergeが許可されている場合のみ（明示依頼、または `AUTO_MERGE_PRIVATE=true` の非公開・非共有repositoryで必要なレビューがすべてLGTM。共通AGENTS §3）：

1. latest head SHA再取得
2. required checks再取得
3. review・thread・verdictの最新性確認
4. 未解決の指摘と未確認範囲を提示
5. merge方式とbranch削除を確認
6. project policyに従ってmerge
7. merge commit/SHA、PR状態、visibilityを報告
