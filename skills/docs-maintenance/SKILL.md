---
name: docs-maintenance
description: Use when README、SPEC、ROADMAP、ADR、公開docs、内部_aiの新規作成、更新、分割、統合、改名、削除、または実装との同期が必要なとき。
---

# Documentation Maintenance

## 使用条件

- 新しい仕様文書を作る
- README、SPEC、ROADMAP、ADRを更新する
- docsを分割、統合、rename、削除する
- code変更に伴う利用方法・API・制限を同期する
- public情報とinternal `_ai/` を分離する

開始時に、このSkill内の `references/documentation.md` を読む。

## 1. inventory

- repository rootと関連docsのfile一覧を確認する。
- 各文書の読者、目的、時間軸、正本を表にする。
- 同じ役割、重複、古いlink、実装と矛盾する記述を特定する。
- 新規fileを作る前に、既存文書へ入らない理由を確認する。

## 2. plan

```markdown
| document | reader | purpose | time horizon | source of truth | action |
|---|---|---|---|---|---|
```

action：keep / update / merge / split / redirect / delete / internalize。

## 3. content

- 現在仕様と将来案を混ぜない。
- 過去の試行錯誤は、現在の理解に必要な結論だけ残し、詳細はgit historyへ任せる。
- code/API/schemaを確認してから正式名称、command、optionを書く。
- READMEでは、projectの価値・利用・評価の入口と、必要な技術根拠を読者に合う順で示す。
- internal strategy、local path、agent作業historyをpublic docsへ出さない。
- user prompt全文をPR・docsへ転載せず、公開してよいrequirementへ要約する。

## 4. synchronization

- implementation、example、command、screenshot、README、SPECの意味を同期する。
- 同じ技術detailを全文書へcopyしない。詳細の正本を1つにし、他はsummary/linkにする。
- multilingual docsが正本として存在する場合、関連箇所を同じchangeで同期する。
- rename/delete時は全参照を検索し、redirectを設置するか、linkを修正する。

## 5. validation

- Markdown linkとlocal path
- command exampleの実行可能性
- option・API・version
- heading/index/navigation
- public/internal information leak
- duplicate source of truth
- stale future/past wording
- 日本語の人間向け文書：textlintの指摘を解消する（編集時hook・pre-commitが自動で指摘する環境では、その指摘に従う）
- 公開・提出する人間向け文書：`assets/DOCS_REVIEW_PROMPT.md` によるfresh contextの読みやすさレビュー（reviewerの資格条件は同ファイル冒頭の指定に従う。round 2既定、`VERDICT: LGTM` まで）

新しく考えた仕様を、その同じcontextで過度に厳密なdocument testへ固定しない。fresh review後に、stableな意味だけをlint/CIで検査する。

## 6. report

- reader/purposeの変更
- source of truth
- merge/split/deleteしたfile
- link・example検証
- public/internalの移動
- 未確認のimplementation detail
