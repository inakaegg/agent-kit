# Common Agents — AIコーディング運用の共通基盤

CodexとClaude Codeで共有できる、個人開発向けのopinionated baselineです。
常時読む共通契約を `AGENTS.md` に絞り、タスクごとの詳しい手順をSkill、
一般ポリシー、template、機械検査へ分離しています。

## 目的

- 権限境界、証拠に基づく検証、外部操作の停止条件を全projectで揃える
- 長い手順を常時contextへ入れず、必要なSkillだけ段階的に読む
- taskの合格条件、作業中の仮説、永続仕様を別の正本へ分ける
- 注意書きだけでなく、test、type、lint、Hook、CI、scriptによる強制を優先する
- CodexとClaude Codeで共通規則を重複管理しない

## 構成

```text
.
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── docs/
│   ├── instruction-placement.md
│   ├── skill-authoring.md
│   └── policies/
│       ├── agent-collaboration.md
│       └── git-and-remote.md
├── skills/                  # 各Skillは SKILL.md と agents/openai.yaml を持つ
│   ├── debug-loop/
│   ├── docs-maintenance/    # + references/documentation.md
│   ├── evaluation-loop/
│   ├── independent-review/  # + assets/REVIEW_PROMPT.md
│   ├── large-work/
│   ├── pair/                # + assets/役割brief 3種 + references（transport-codex、設計ノート）
│   ├── pr-review-loop/
│   └── ui-verification/
├── templates/
│   ├── ACTIVE_PLAN.md
│   ├── PROJECT_AGENTS.md
│   ├── TASK.md
│   └── VERIFICATION.md
├── scripts/
│   ├── agent-check.example.sh
│   └── validate-kit.py
└── tests/
    └── test_public_bundle.py
```

各Skillは単独で配置しても参照が壊れないよう、必要なreferenceやassetを
同じSkill directory内に保持します。

## 導入

既存ファイルがある場合は上書きせず、内容とsymlink先を確認してから切り替えてください。
以下の `/absolute/path/to/common-agents` はclone先の絶対pathへ置き換えます。

### Codex

Codexはグローバル指示を `~/.codex/AGENTS.md`、ユーザーSkillを
`~/.agents/skills/` から読みます。

```bash
agent_kit_dir="/absolute/path/to/common-agents"

mkdir -p "$HOME/.codex" "$HOME/.agents/skills"
ln -s "$agent_kit_dir/AGENTS.md" "$HOME/.codex/AGENTS.md"
ln -s "$agent_kit_dir" "$HOME/.codex/agent-kit"

for skill_dir in "$agent_kit_dir"/skills/*; do
  skill_name="${skill_dir##*/}"
  ln -s "$skill_dir" "$HOME/.agents/skills/$skill_name"
done
```

`CODEX_HOME`を設定している場合は、`~/.codex` の代わりにそのdirectoryを使います。

### Claude Code

Claude Codeはユーザー指示を `~/.claude/CLAUDE.md`、ユーザーSkillを
`~/.claude/skills/` から読みます。`CLAUDE.md` は隣の `AGENTS.md` をimportする
薄いadapterです。

```bash
agent_kit_dir="/absolute/path/to/common-agents"

mkdir -p "$HOME/.claude/skills"
ln -s "$agent_kit_dir/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
ln -s "$agent_kit_dir/AGENTS.md" "$HOME/.claude/AGENTS.md"

for skill_dir in "$agent_kit_dir"/skills/*; do
  skill_name="${skill_dir##*/}"
  ln -s "$skill_dir" "$HOME/.claude/skills/$skill_name"
done
```

### 個人環境ポリシー

端末固有のmodel保存先、timezone、local log、path検査は公開bundleへ含めません。
必要な利用者だけ `~/.codex/local-policies/local-environment.md` を作成します。
共通 `AGENTS.md` と `$large-work` は、このファイルが存在する場合だけ読みます。

## Projectへの適用

1. `templates/PROJECT_AGENTS.md` を基に、project固有の短い `AGENTS.md` を作る。
2. 実在するbuild・lint・test commandを `templates/VERIFICATION.md` の形で記録する。
3. taskの合格条件は `templates/TASK.md`、作業中の仮説と進捗は
   `templates/ACTIVE_PLAN.md` から作る。
4. 共通規則へ追記する前に `docs/instruction-placement.md` で置き場所を判定する。

## 検証

```bash
python3 scripts/validate-kit.py
python3 -m unittest discover -s tests -v
```

検証は、必須ファイル、Skill frontmatter、参照先、個人・端末固有情報、
`AGENTS.md` の大きさ、Claude adapterを確認します。

## 対応する公式仕様

- [Codex: Custom instructions with AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md)
- [Codex: Build skills](https://developers.openai.com/codex/build-skills)
- [Claude Code: How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/slash-commands)

## 意図的に共通化しないもの

- 特定のpackage manager、framework、coding style
- すべてのbugやfeatureに対するIssue作成
- 特定のreview bot、workflow、merge方式
- 元のユーザープロンプト全文の公開
- 個人PCの絶対path、cache、credential、local policy

これらはprojectの `AGENTS.md`、lint・CI、個人設定、非公開policyへ置きます。

## License

MIT License（`LICENSE` を参照）。
