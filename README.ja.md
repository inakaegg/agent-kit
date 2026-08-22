# agent-kit — AIコーディングエージェントの運用キット

🇬🇧 English: [README.md](README.md)

CodexとClaude Codeの両方で共用する、作業規約（`AGENTS.md`）、タスク別の手順書（Skill）、
テンプレート、検査スクリプトのセットです。汎用の雛形ではなく、個人開発の実運用で
使っている構成をそのまま固めたもの（いわゆるopinionated）です。

エージェントが常時読み込むのは160行の `AGENTS.md` だけに絞り、詳しい手順はSkillへ、
タスクの合格条件・作業中の仮説・恒久仕様はそれぞれ別のファイル（`templates/` 参照）へ、
機械的に判定できる規則は検査スクリプトへ分離しています。権限境界（push・公開・課金は
明示許可制）と停止条件を、CodexとClaude Codeの区別なく全プロジェクトで揃えるのが役割です。

## 設計の考え方

1. **規則は文書ではなく機械で強制する** — 規約文書（`AGENTS.md`）に書くだけでは、
   エージェントは従ったり従わなかったりする。そのため規約文書は入口に留め、破ると
   失敗する検査（`scripts/validate-kit.py`、`git-hooks/` のpre-commit・pre-push、テスト）を本体とする。
   文章での注意が増えてきた規則は、lint・test・Hook・CIへ移す
   （置き場所の判定手順は `docs/instruction-placement.md`）。
2. **完全自動ループは、合格を機械判定できる閉じたタスクに限る** — 一括migrationや
   lint掃討のように「done」をテストや数値で判定できる作業以外では、エージェントを
   無人で回さない。ソフトウェア開発の大半は、作っている途中で不明確な点が現れ、
   質問と判断を通じて仕様が固まっていく。だから既定は、自走距離を伸ばしつつ本当の
   判断点でだけ人間へ戻す**監督付き並行体制**とする
   （実装役＋監視役の2セッション、`skills/pair/`）。
3. **検証は自己申告ではなく証拠で** — 非自明な変更は、実装した本人とは別の文脈の
   レビュアーがgate制で検査する（`skills/independent-review/`）。実行していない
   コマンドを実行済みと報告しない、という規則が全体の土台にある。
4. **高コストな検査は境界に置き、編集のたびには走らせない** — 編集1回ごとに
   LLMの監査や注意喚起を挟む方式は、コストが高いうえ、繰り返される注意はすぐ
   効かなくなる。意味の検査（読みやすさ・整合性）は公開・提出前のレビューgate
   （`skills/docs-maintenance/`）へ、機械判定できる検査（絶対パス混入・秘密情報・
   日本語lint）はcommit・pushのGit hookへ置く。例外は決定論的で安価なlintで、
   これだけは編集直後の即時フィードバック（後述のtextlint hook）にも使う。
   指摘がなければ無音のため、繰り返しても注意が摩耗しないからである。

## 構成

```text
.
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── README.ja.md
├── .textlintrc.json         # 日本語文書lintの規則（pre-commitが参照）
├── prh.yaml                 # 用語辞書（レビュー指摘から育てる）
├── docs/
│   ├── instruction-placement.md
│   ├── skill-authoring.md
│   └── policies/
│       ├── agent-collaboration.md
│       └── git-and-remote.md
├── git-hooks/
│   ├── pre-commit           # 環境依存の絶対パス混入をcommit時に拒否
│   └── pre-push             # push前にgitleaksで秘密情報を走査（初回pushは全履歴）
├── skills/                  # 各Skillは SKILL.md と agents/openai.yaml を持つ
│   ├── architecture-diagram/ # + assets/diagram_template.py、references/pitfalls.md
│   ├── ci-fix/
│   ├── debug-loop/
│   ├── dep-upgrade-safe/
│   ├── docs-maintenance/    # + references/documentation.md
│   ├── evaluation-loop/
│   ├── independent-review/  # + assets/REVIEW_PROMPT.md
│   ├── large-work/
│   ├── pair/                # + assets/役割brief 3種 + references（transport-codex、設計ノート）
│   ├── pr-review-loop/
│   ├── semantic-generation/ # + references/referent-before-label.md
│   ├── ui-quality/          # + references（web、native、audit-rubric）
│   └── ui-verification/
├── templates/
│   ├── ACTIVE_PLAN.md
│   ├── PROJECT_AGENTS.md
│   ├── TASK.md
│   └── VERIFICATION.md
├── scripts/
│   ├── agent-check.example.sh
│   ├── textlint-hook.py     # Claude Code用: .md編集直後の即時lint
│   └── validate-kit.py
└── tests/
    └── test_public_bundle.py
```

各Skillは単独で配置しても参照が壊れないよう、必要なreferenceやassetを
同じSkill directory内に保持します。

`pair` skillは、英語の独立プラグイン [pair-watch](https://github.com/inakaegg/pair-watch) としても公開しています（Claude Codeのplugin marketplaceから導入可）。

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

### Git hooks

このhookはエージェント専用の機能ではなく、Gitの標準機構です。エージェントにも人間にも
同じ規約を強制する最終防衛線としてキットに含めています。
`git-hooks/` を全リポジトリ共通のhook置き場として `core.hooksPath` に設定します。

```bash
git config --global core.hooksPath /absolute/path/to/agent-kit/git-hooks
```

- `pre-commit` は、環境依存の絶対パス（ホームディレクトリ配下、外部ボリューム配下）が
  staged diffの追加行へ混入したcommitを拒否します。
- `pre-commit` は続けて、staged対象の `.md` を [textlint](https://textlint.org/)
  （日本語の技術文書lint）で検査します。全リポジトリで既定有効です。リポジトリ直下に
  `.textlintrc.json` 等の設定があればそれを優先し、なければこのkit同梱の
  `.textlintrc.json`（文の長さ、冗長表現、漢字の連続など）と `prh.yaml`（用語辞書）で
  検査します。検査しないリポジトリでは `git config --local hooks.skipTextlint true` を
  設定します。指摘のうち自動修正できる分（用語辞書、数字表記など）はworking treeへ
  適用しますが、そのままcommitには入れず一度止めます。機械の修正が過剰なことも
  あるため、人間が差分を確認してstageし直してから再commitします。
<!-- textlint-disable prh -->（悪い例の引用のため、次の1文だけ用語辞書の検査を除外）
  辞書には、レビューで実際に指摘された「読者に伝わらない語」（縮退→フォールバック等）を
  登録し、同型の指摘が2件以上出た語を追加して育てます。
<!-- textlint-enable prh -->
  textlint未導入の環境では警告だけ出して通します。kit同梱の設定・辞書へ足してよいのは
  全プロジェクトに通用する項目だけで、特定プロジェクトの都合で緩めたい場合は
  そのリポジトリ直下の設定（上記の優先機構）で行います。有効化は次の1回だけです。

  ```bash
  npm install -g textlint textlint-rule-preset-ja-technical-writing \
    textlint-rule-prh textlint-filter-rule-comments
  ```

- `pre-push` は、push対象のcommit範囲（初回pushは到達可能な全履歴）をgitleaksで走査し、
  秘密情報らしき値を検出したらpushを拒否します。gitleaks未導入の環境では警告だけ出して
  pushを通します（`brew install gitleaks` で有効化）。
- リポジトリ固有の `.git/hooks/` がある場合は検査後に委譲します。意図的に絶対パスを
  許可するリポジトリでは `git config --local hooks.allowLocalPaths true` を設定します。

### 編集時の即時lint（Claude Code）

Claude Codeでは、エージェントが `.md` を編集・作成した直後にtextlintを実行し、
指摘をその場で修正させられます。`~/.claude/settings.json` へ次のhookを登録します。
指摘がないときは何も出力しません。`_ai/` などエージェント専用の内部文書は対象外です。

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/agent-kit/scripts/textlint-hook.py"
          }
        ]
      }
    ]
  }
}
```

この登録は、textlintの導入（前節の `npm install`）と同じく、利用者が各自で行う
手作業です。自動で実行されるコマンドの登録は、人間が自分の設定へ書くべきもの
なので、エージェントに代行させません（Claude Code側も、エージェントによる
この設定の書き込みを自動では承認しません）。

Codexには同等のhook機構がないため、Codex側はcommit時のpre-commitと
`$docs-maintenance` の手順でカバーします。

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
