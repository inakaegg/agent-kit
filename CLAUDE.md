# CLAUDE.md

@AGENTS.md

リポジトリ規則の正本は `AGENTS.md` とする。Claude Code固有の設定、Hook、Skill登録だけをこのファイルまたは `.claude/` 配下へ置き、共通規則を重複記載しない。

`AGENTS.md` に列挙されたSkill・policyは、現在の作業に該当するときだけ読む。すべてを起動時にimportしない。

`AGENTS.md` 内の `$<name>` 表記は同名のSkillを指す。Claude CodeではSkillツールでその名前のSkillを呼び出す。

プラグインや外部Skillの指示が `AGENTS.md` と矛盾する場合は、`AGENTS.md` を優先する。重複する領域では `AGENTS.md` が参照する自作Skillを使う。

外部Skill `natural-japanese`（日本語文書の執筆・推敲）を導入済み。README・SPEC・ROADMAP・ADR等のdocs工程では `$docs-maintenance` を正とし、natural-japaneseは文章の執筆・推敲層としてだけ使う。repo管理下の文書をnatural-japaneseでリライトする際は、textlint制御コメント・front matter・既存の文書規約（`CLI.md` の表のみ規則等）を保持する。
