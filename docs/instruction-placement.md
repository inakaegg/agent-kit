# 指示をどこへ置くか

## 判定順

新しい注意事項やworkflowが生まれたときは、次の順で置き場所を決める。

1. **機械的に検出・拒否できるか**
   - Yes → test、type、lint、schema、Hook、CI、wrapper script
2. **今回のtaskだけか**
   - Yes → `_ai/TASK.md`、Issue、task spec
3. **作業中に変わる仮説・進捗か**
   - Yes → `_ai/active-plan.md`
4. **特定projectだけか**
   - Yes → projectの `AGENTS.md`、project docs
5. **特定directory・moduleだけか**
   - Yes → nested `AGENTS.md`、architecture test
6. **繰り返す複数step workflowか**
   - Yes → Skill、script、runbook
7. **個人PC・個人好みだけか**
   - Yes → local policy、tool設定、memory
8. **設計理由か**
   - Yes → ADR
9. **ほぼ全taskへ長期間必要で、機械化できないか**
   - Yes → 共通 `AGENTS.md`

## 配置表

| 内容 | 置き場所 |
|---|---|
| push・公開・課金の権限境界 | 共通 `AGENTS.md` |
| 現在のgoal、scope、acceptance | `_ai/TASK.md` |
| 現在の仮説、試行、次の一手 | `_ai/active-plan.md` |
| build・lint・testの正確なcommand | project `AGENTS.md` / `docs/quality/verification.md` |
| framework・package manager・coding style | project `AGENTS.md` / lint / formatter |
| 禁止API・禁止import | lint / architecture test |
| PR review反復 | Skill |
| UI確認手順 | Skill |
| model保存先・JST表示 | local policy |
| public product spec | `docs/` / `SPEC.md` |
| 将来方針 | `ROADMAP.md` |
| 設計理由 | ADR |
| troubleshooting | runbook / debugging Skill |

## 共通AGENTSへ追加する5条件

次をすべて満たさない規則は、共通AGENTSへ追加しない。

1. ほとんどのproject・taskに適用される
2. 数か月後も有効である見込みが高い
3. 作業開始前に知る必要がある
4. toolingでより確実に強制できない
5. 他の正本を複製せず短く書ける

## 失敗から学ぶとき

```text
失敗
  ↓
再現可能か
  ├─ Yes → regression test / lint / type / Hook / CI
  └─ No
       ↓
繰り返すworkflowか
  ├─ Yes → Skill / script
  └─ No
       ↓
project固有か
  ├─ Yes → project AGENTS / docs
  └─ No → 共通AGENTS候補をユーザー確認
```

## メモリの定期監査

エージェントが自身の永続メモリ（Claude Codeのprojectメモリ等）へ書いた内容は、規則の正本ではない。放置すると既存規則との重複や古い記述が溜まるため、定期的（kit改訂時、目安として月1回）に次を行う。

1. 全projectのメモリファイルを一覧し、各entryを上の判定順にかける。
2. 複数projectへ一般化できる規則・教訓は、共通/projectの `AGENTS.md`、Skill、toolingへ吸い上げてから元のメモリを削除する。
3. 既存規則と重複するメモリ、事実が古くなったメモリは削除する。吸い上げ済みかの判断に迷うものはユーザーへ確認する。
