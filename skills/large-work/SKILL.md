---
name: large-work
description: Use when 30分以上、100件超、大量token・外部料金・GPU・storage、大規模migration・annotation・網羅調査など、段階的pilotと停止条件が必要な作業。
---

# Large Work

## 使用条件

次のいずれかに該当する場合に使う。

- 30分以上の連続処理または複数turnの自動継続が見込まれる
- 100件を超えるannotation、review、変換、manual judgement
- 大量token、API料金、GPU、storage、networkを消費し得る
- 全件処理、網羅調査、大規模migration、長時間monitoring
- 失敗時の手戻りが大きい
- 方式の有効性が少数件で確認されていない

## 1. 開始前のtask contract

次を明記する。

- 利用者・製品・運用の何が改善するか
- input件数と対象範囲
- output artifact
- baselineと最小構成
- quality metric
- 形式品質 / 意味妥当性 / 製品価値の別metric
- 1件・1batch・全体のtime/token/cost/storage概算
- checkpoint
- acceptanceとstop条件
- external write、課金、公開範囲

課金、大量download、remote writeがある場合は、実行前に明示確認を得る。

## 2. 方式の事前審査

順番：

1. OS標準、既存library、公開規格、公式data、既存実装、licenseを確認
2. 既存処理をそのまま使う最小構成を試す
3. 使い分け、候補提示、非破壊的補完、fallbackを試す
4. 不足が実証された範囲だけ独自方式を作る

corpus、評価基盤、migration script等の中間成果物を、製品成果そのものとみなさない。

## 3. 段階的pilot

既定：

1. 10〜20件のpreflight
2. 50〜100件のsmall batch
3. 合格後に適切なbatch sizeで残件

各段階で：

- 成功・失敗・要review件数
- quality metric
- representative artifact
- time/token/cost/resource
- false positive/negativeまたはregression
- 次段階へ進む根拠

を記録する。checkpoint合格前に残件を自動開始しない。

## 4. 実行状態

`_ai/active-plan.md` または専用state fileへ残す。

```markdown
## Batch N
- input range:
- started_at:
- config/version:
- completed / failed / skipped:
- metrics:
- cost/resource:
- artifacts/logs:
- decision: continue / revise / stop
```

長時間logは、存在する場合は `~/.codex/local-policies/local-environment.md` のlocal既定に従い、常にproject規則を優先する。再開可能なcheckpointと、重複処理を避けるidempotent keyを用意する。

## 5. 品質管理

- `valid=true`、schema pass、件数完了を、意味・期待値・製品価値の証拠にしない。
- 同じinputを複数担当が一致して処理したことは再現性の証拠であり、外部事実の正しさとは分ける。
- samplingだけで全件品質を断定しない。sampling designとconfidence limitationを示す。
- batch途中でprompt、rule、model、parameterを変えた場合はversionを分け、同一条件の結果として集計しない。
- 既に使ったtime/tokenを理由に、非改善方式へ追加投資しない。

## 6. 停止条件

既定の停止条件：

- preflightまたはsmall batch不合格
- 見積りの2倍超過
- 同じ方式の大きな改訂2回
- 2checkpoint連続で製品metricが横ばい・悪化
- cost上限、storage上限、error率上限へ到達
- external contract・license・privacy問題が判明
- 人間の意味判断なしに品質を確定できない

停止時は残件を続行せず、観測事実、費用、artifact、代案、安全な再開点を報告する。
