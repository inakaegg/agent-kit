# CLAUDE.md

@AGENTS.md

リポジトリ規則の正本は `AGENTS.md` とする。Claude Code固有の設定、Hook、Skill登録だけをこのファイルまたは `.claude/` 配下へ置き、共通規則を重複記載しない。

`AGENTS.md` に列挙されたSkill・policyは、現在の作業に該当するときだけ読む。すべてを起動時にimportしない。

`AGENTS.md` 内の `$<name>` 表記は同名のSkillを指す。Claude CodeではSkillツールでその名前のSkillを呼び出す。

プラグインや外部Skillの指示が `AGENTS.md` と矛盾する場合は、`AGENTS.md` を優先する。重複する領域では `AGENTS.md` が参照する自作Skillを使う。

外部Skill `natural-japanese`（日本語文書の執筆・推敲）を導入済み。README・SPEC・ROADMAP・ADR等のdocs工程では `$docs-maintenance` を正とし、natural-japaneseは文章の執筆・推敲層としてだけ使う。repo管理下の文書をnatural-japaneseでリライトする際は、textlint制御コメント・front matter・既存の文書規約（`CLI.md` の表のみ規則等）を保持する。

外部ライティングSkillとして `japanese-tech-writing`（論証・段落構成・読み手の負荷）と `cognitive-rhythm-writing`（読み物の緩急設計）も試験導入済み（出所と削除手順は各Skillディレクトリの `SOURCE.md`）。層分けは次のとおり。技術文書・解説文の論理構造と論証はjapanese-tech-writing、文の自然さ・AI臭さ除去はnatural-japanese、記事・章・エッセイなど読み物の緩急だけcognitive-rhythm-writingを使う。cognitive-rhythm-writingをdocs工程（README・SPEC等）へ適用しない。japanese-tech-writingの整形規則（一文一行改行・中黒禁止等）がrepoの文書規約やtextlint設定と矛盾する場合は、repo側を優先する。

外部Skill `grill-me`（実体は `grilling`）を試験導入済み。計画・設計の要件出しをユーザーが明示的に求めたときだけ使い、`_ai/tasks/` の契約（TASK.md）を書く前の段階に限る。AGENTS.md §7の独立レビューの代替にしない。

待ち時間のキャッシュ維持。外部の事象（レビュー担当の再開時刻、CIの完了など）を待つあいだにセッションがprompt cacheのTTL（現時点で1時間）以上無操作になると、cacheが切れて次の起床で文脈全体を再読込する。**再開・完了の見込み時刻が立つ場合に限り**、必要な監視（`Monitor` 等）の張り直しをTTLより十分短い間隔（目安はTTLの9割以下。応答や起床の遅れでTTLを越えないため）で行ってキャッシュを保ってよい（`CACHE_KEEPALIVE=true`）。維持1回の費用は通常の1ターンと同じく文脈のcache読み1回分で、冷えてからの再読込より小さい。張り直しは1つの待ちにつき `CACHE_KEEPALIVE_MAX`（既定3回）までとし、見込み時刻までの残りが上限×間隔＋TTL（最後の張り直しで保てる分）を超えるなら最初から維持しない。上限に達したら短い間隔での張り直しをやめて冷えるに任せ、チャットへ1行報告する。待ち自体の監視は必要なら続ける（間隔はTTL以上でよい）。維持のための起床では他の作業を始めない。見込み時刻が立たないとき（ユーザーの返答待ちなど）は行わない。
