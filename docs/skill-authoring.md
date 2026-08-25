# Skillの作成と改訂

この文書はSkillを新規作成・改訂するときだけ読む。

## Skillにするかの判定

次をすべて満たすときだけSkillにする。満たさないものは、project docs、task契約、toolingへ置く（`docs/instruction-placement.md` の判定順に従う）。

- 複数のproject・taskで繰り返す複数stepのworkflowである
- 手順を知らないと結果の質が変わる
- test・lint・Hook・CIでは強制できない判断を含む

## 構成

- 1 Skill = 1 workflow。複数の関心事を1つのSkillへ詰めない。
- `SKILL.md` は手順・使用条件・停止条件だけを短く書く。長い背景、rubric、checklist、prompt本文は `references/`・`assets/` へ分離する。
- Skill directory単体で参照が完結するようにし、repository内の他ファイルへの相対参照を作らない。
- 共通 `AGENTS.md` や他のpolicyの内容を複製しない。必要なら名前で参照する。
- Codex互換のため `agents/openai.yaml` を併設する。

## frontmatterとdescription

- `name` はkebab-caseで動作を表す。
- `description` は「いつ使うか」を第三者視点で書く。発火させたい状況、症状、ユーザーの言い回し、キーワードを具体的に含める。内容の要約だけにしない。
- 使わない条件（対象外）が紛らわしい場合は、descriptionまたは使用条件に明記する。

## 本文の書き方

- 会話の文脈を持たない将来のagentが読む前提で書く。今回のtask固有の値、日付、環境依存の絶対pathを書かない。
- 手順は実行順に番号を振り、各stepの完了判定を書く。
- 逸脱しやすい点は、禁止事項ではなく「誤った近道 → 正しい行動」の形で書く。
- 停止条件と上限（反復回数、attempt数、cost）を必ず含める。

## 配備前の検証

1. `python3 scripts/validate-kit.py` を通す（frontmatter、参照先、個人情報混入を検査）。
2. 履歴を共有しない別セッションのagentへ実taskを与え、Skillだけを頼りに手順どおり動けるかを1回試す。
3. 手順を誤読・skipした箇所があれば、agentではなくSkillの記述を直す。

## 保守

- Skillが現場で失敗したら、同じ失敗を防ぐ最小の記述を足す。一般論を足さない。
- 機械判定できる規則へ育った項目は、Skillからlint・test・Hookへ移す。
- 使われなくなったSkillは残さず削除し、README・AGENTSの参照を更新する。
