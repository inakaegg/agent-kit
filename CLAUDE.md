# CLAUDE.md

@AGENTS.md

リポジトリ規則の正本は `AGENTS.md` とする。Claude Code固有の設定、Hook、Skill登録だけをこのファイルまたは `.claude/` 配下へ置き、共通規則を重複記載しない。

`AGENTS.md` に列挙されたSkill・policyは、現在の作業に該当するときだけ読む。すべてを起動時にimportしない。

`AGENTS.md` 内の `$<name>` 表記は同名のSkillを指す。Claude CodeではSkillツールでその名前のSkillを呼び出す。

プラグインや外部Skillの指示が `AGENTS.md` と矛盾する場合は、`AGENTS.md` を優先する。重複する領域では `AGENTS.md` が参照する自作Skillを使う。

外部Skillは、利用可能なものだけを必要時に使う。未導入でも、文書作業は `$docs-maintenance` と `docs/policies/writing-and-docs.md` で続行する。インストールや個人設定の変更を前提にしない。

- `natural-japanese`：日本語の文の自然さを整える補助手段。README・SPEC等のdocs工程は `$docs-maintenance` を正とする。リライト時もtextlint制御コメント・front matter・既存の文書規約（`CLI.md` の表のみ規則等）を保持する。
- `japanese-tech-writing`：技術文書・解説文の論理構造と論証を整える。整形規則（一文一行改行・中黒禁止等）がrepoの文書規約やtextlintと矛盾する場合はrepo側を優先する。
- `cognitive-rhythm-writing`：記事・章・エッセイ等の読み物の緩急に限って使い、README・SPEC等のdocs工程へは適用しない。
- `grill-me`（実体は `grilling`）：ユーザーが計画・設計の要件出しを明示的に求めたとき、TASK作成前だけ使う。未導入ならAGENTS §4の理解・実物確認・契約固定で整理し、不足する判断をユーザーへ確認する。独立レビューの代替にしない。

待ち時間のキャッシュ維持。外部の事象（レビュー担当の再開時刻、CIの完了など）を待つあいだにセッションがprompt cacheのTTL（現時点で1時間）以上無操作になると、cacheが切れて次の起床で文脈全体を再読込する。**再開・完了の見込み時刻が立つ場合に限り**、必要な監視（`Monitor` 等）の張り直しをTTLより十分短い間隔（目安はTTLの9割以下。応答や起床の遅れでTTLを越えないため）で行ってキャッシュを保ってよい（`CACHE_KEEPALIVE=true`）。維持1回の費用は通常の1ターンと同じく文脈のcache読み1回分で、冷えてからの再読込より小さい。張り直しは1つの待ちにつき `CACHE_KEEPALIVE_MAX`（既定3回）までとし、見込み時刻までの残りが上限×間隔＋TTL（最後の張り直しで保てる分）を超えるなら最初から維持しない。上限に達したら短い間隔での張り直しをやめて冷えるに任せ、チャットへ1行報告する。待ち自体の監視は必要なら続ける（間隔はTTL以上でよい）。維持のための起床では他の作業を始めない。見込み時刻が立たないとき（ユーザーの返答待ちなど）は行わない。
