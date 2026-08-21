---
name: evaluation-loop
description: >-
  Use when adoption is decided by measurement: heuristics / ranking / OCR・ASR・translation・generation
  quality / rival implementations compared on the same data. Japanese cues: 「同一データで比較」「実測で採否」「品質を評価」.
---

# Evaluation Loop

## 使用条件

- 「どの方式が良いか」を実測で決める
- 独自heuristic、補正、ranking、fallbackを追加する
- OCR、ASR、翻訳、音声、画像、LLM output等、単純なpass/failだけで品質を表せない
- parameter・condition・ON/OFFの組合せを比較する
- 性能、cost、resource、保守性を含めて選択する

## 1. 製品上の目的を一文で固定する

中間成果物ではなく、利用者に起きる改善を書く。

悪い例：

```text
辞書を1万件作る。
```

良い例：

```text
字幕の固有名詞誤認を減らし、利用者が手修正せず学習を続けられる割合を上げる。
```

形式品質、意味の正しさ、製品上の価値を別々に測る。

## 2. 事実と制約を確認する

- 保存済みdata、実fixture、response、schemaを最低1件開く。
- `存在しない`、`対応付けられない` 等の否定を、実物未確認で制約にしない。
- task文書では、`User requirements / Confirmed facts / Assumptions` を分ける。
- assumptionを制約として採用する場合、確認しない理由と外れた影響を書く。

## 3. baselineと候補を列挙する

最低限、次を候補に含める。

1. 現状維持
2. 既存処理をそのまま使う
3. 利用者または用途で既存処理を使い分ける
4. 既存結果を変えない情報補完
5. failure時だけfallback
6. 不足が実証された範囲の独自処理

設計上「賢そう」な案を採用決定とせず、検証候補として扱う。

## 4. dataを分割する

- **development/tuning set**：方式・parameterの調整に使う
- **held-out set**：最終候補が決まるまで見ない
- **regression set**：変更前に正常だった代表例
- **boundary/adversarial set**：空、長文、異常、曖昧、複数候補、rare case

報告された問題例だけで評価しない。候補ごとに有利なdataへ差し替えない。

## 5. 実験を設計する

候補数が現実的なら、同じdata・同じmetricで全組合せを自動比較する。組合せが爆発する場合は、影響の大きい軸から範囲を事前限定し、「全組合せを確認した」と報告しない。

記録項目：

| candidate | improved | regressed | unchanged | time | memory/cost | rules/states/deps | notes |
|---|---:|---:|---:|---:|---:|---:|---|

自動scoreだけで利用者価値を判断できない場合は、blindな代表output比較または人間の評価を併用する。

## 6. 独自heuristicの採用条件

次をすべて満たす場合だけ採用する。

1. 実利用上の問題が複数例で確認される
2. 個別inputではなく一般的な成立条件を説明できる
3. 現状維持、既存方式、選択肢提示、補完、fallbackでは解決できない
4. 同じdataで改善数と悪化数を比較できる
5. 正常だった代表例を守るregression testがある
6. held-outでも改善し、明白な悪化がない
7. 改善がcomplexity、runtime、cost、maintenance増に見合う

「既存結果を変更する正解判定」と、「情報補完」「候補表示」「UI/state整合性」を混同しない。

## 7. 選択規則

- 同程度なら、規則、state、dependency、maintenance箇所が最も少ない案を選ぶ。
- 僅かな数値改善のために大幅な複雑化を選ばない。
- 1metricの改善で、別metricや正常caseの悪化を隠さない。
- performance claimには同じ環境のBefore/Afterを付ける。
- costを含む場合は、1件、1batch、想定月間量の単位を分ける。

## 8. loop

```text
baseline
→ candidate実装
→ 同一dataで測定
→ failure/regression分類
→ validな修正
→ development set再測定
→ held-out確認
→ fresh-context review
→ 採用 / 棄却 / 人間判断
```

## 停止条件

- held-outで改善しない
- 改善と悪化が同程度で、利用者価値を説明できない
- 2回の大きな改訂後もmetricが改善しない
- 見積りの2倍を超えるcost/resourceが必要
- 独自方式なしの最小構成で目的を十分達成できる

停止時も、失敗した方式、data、metric、artifactを残し、同じ実験を後で繰り返さない。
