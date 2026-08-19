---
name: debug-loop
description: Use when 原因が明白でないbug、回帰、flaky failure、非同期・状態・分散問題、同型の複数不具合、または1回目の修正で直らない問題。
---

# Debug Loop

## 使用条件

次のいずれかで使う。

- 原因が明白でないbug、regression、flaky failure
- 非同期、retry、cache、lifecycle、複数environment、分散処理が関係する
- 同型のtest failureまたはreview findingが2件以上ある
- 1回目の修正で直らない、または別の症状へ移った
- error messageと実際に失敗した層が一致しているか不明

単純なtypoや、失敗箇所と修正が一意な小変更へ形式的に適用しない。

## 原則

- root causeを確認する前にhardcode、delay追加、JSON整形回避、例外握り潰し等のquick fixを入れない。
- error stringだけを原因の証拠にしない。code path、state、log、reproductionで裏付ける。
- 観測事実、原因候補、未確認事項、利用者向け対処を分ける。
- 1回の試行では、主仮説と予測する観測signalを1つに絞る。

## 1. 症状と契約を固定する

`_ai/TASK.md` またはactive planへ記録する。

```markdown
## 症状
- 入力・操作:
- 実際の結果:
- 期待結果:
- 発生環境・version:
- 再現率:

## 証拠
- log / stack trace:
- failing test:
- artifact:

## 未確認
- ...
```

期待値は、user requirement、product spec、責任分界、既存の正常挙動から確認する。実装と同時に書いたtestだけを期待値の根拠にしない。

## 2. 決定的な再現を作る

優先順位：

1. 最小のfailing unit test
2. 固定fixtureによるintegration test
3. 再現script
4. manual procedureとlog/artifact

- 変更前にfailureを確認する。
- 外部API、clock、random、filesystem、process、networkは可能な限り注入・fake化する。
- 「たまに起こる」は、seed、timing、state transition、並行順序を記録して狭める。
- 再現できなければ、修正よりinstrumentation追加を優先する。

## 3. 実行経路と境界を図にする

特に分散・非同期処理では、次を表にする。

| 段階 | 実行主体・environment | 入力 | state | 次へ渡すもの | 実行しない条件 | failureの見え方 |
|---|---|---|---|---|---|---|

- errorが起きた層と、後続で呼ぶ予定だった層を混同しない。
- cache、保存済みstate、古いprocess、network restriction、permissionを、直接原因と周辺課題に分ける。
- retry/replayでは、idempotency、duplicate side effect、stale callback、generation/token、cancel条件を確認する。

## 4. 履歴と既存patternを調べる

regressionの可能性がある場合：

- `git log -S` または `git log -G`
- `git blame`
- 関連commit・PRのdiff
- 同じAPI・state transition・error handlingの他call site

履歴未確認なら「いつ、なぜ導入されたか」を断定しない。現在codeから分かる事実と推測を分ける。

## 5. bug familyを横断監査する

同型問題が2件以上なら、1件ずつ直さずmatrixを作る。

例：

| 軸 | 値 |
|---|---|
| operation | create / update / retry / cancel |
| state | idle / loading / success / error / stale |
| environment | local / CI / production / Windows / macOS |
| visibility | foreground / background |
| data | empty / normal / boundary / invalid |

- 全call siteを検索する。
- 共通不変条件を1つに言語化する。
- 可能ならshared helper、type、state machine、schemaへ集約する。
- 1箇所だけpatchして同じ欠陥を残さない。

## 6. 仮説検証loop

各attemptをactive planへ残す。

```markdown
### Attempt N
- 仮説:
- この仮説が正しければ観測されるsignal:
- 最小変更・計測:
- 観測結果:
- 仮説の判定: supported / rejected / inconclusive
- 次の一手:
```

- 仮説をrejectした証拠を消さない。
- 同じ仮説を表現だけ変えて再実行しない。
- 新しいinformationがないまま依存upgrade、全面rewrite、delay増加へ飛ばない。

## 7. 修正

- failureを生む不変条件の破れを修正する。
- 可能なら回帰testを先に失敗させる。
- 正常だった隣接caseを守るtestも必要に応じて追加する。
- retryやfallbackを追加する場合、failureを隠さず、発火条件、上限、観測方法を定義する。
- debug log・一時assert・fixture改変の残骸を除く。

## 8. 検証

1. 最小再現がpassする
2. 旧実装またはmutated implementationでregression testが実際にfailすることを確認できるなら確認する
3. 同じbug familyのmatrixを再確認する
4. targeted test
5. projectのfull gate
6. 実artifactまたはmanual smoke
7. final diff review

## 停止条件

- 大きな方針転換3回
- 2attempt連続で予測signalも新情報も得られない
- baseline failureで比較不能
- 未許可のmigration、破壊的変更、課金、security判断が必要
- product requirement自体が矛盾または未決定

停止時は、判明事項、不明点、rejectした仮説、再現、追加で必要な情報、安全な暫定案を報告する。
