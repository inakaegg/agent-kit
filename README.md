# agent-kit — an operations kit for AI coding agents

🇯🇵 日本語ドキュメント: [README.ja.md](README.ja.md)

A set of working rules (`AGENTS.md`), task-specific playbooks (skills), templates, and verification scripts shared by Codex and Claude Code. This is not a generic boilerplate: it is the setup I actually run for solo development, frozen as is (opinionated by design).

Agents always load only the 160-line `AGENTS.md`. Detailed procedures live in skills. Task acceptance criteria, working hypotheses, and durable specs live in separate files (see `templates/`). Machine-checkable rules live in verification scripts. The kit's job is to keep permission boundaries and stop conditions identical across Codex and Claude Code on every project. Push, publication, and billing always require explicit human approval.

## Design principles

1. **Enforce rules with machines, not documents**. Rules that exist only in a policy document get followed inconsistently. So the policy document stays a thin entry point. The real enforcement is checks that fail when a rule is broken: `scripts/validate-kit.py`, the pre-commit and pre-push hooks in `git-hooks/`, and tests. When written reminders about the same rule keep accumulating, the rule moves into lint / tests / hooks / CI. The placement procedure is `docs/instruction-placement.md`.

2. **Fully autonomous loops are only for closed tasks with machine-checkable success**. Except for work whose "done" can be judged by tests or numbers — bulk migrations, lint sweeps — agents are not run unattended. Most software development surfaces unclear points mid-build, and the spec settles through questions and decisions. So the default is a supervised pair setup: implementer plus watcher across two sessions (`skills/pair/`). Extend the autonomous stretch, but return to a human exactly at the real decision points.

3. **Verification means evidence, not self-report**. Non-trivial changes are reviewed through gates by a reviewer whose context is separate from the implementer's (`skills/independent-review/`). The foundation under everything else is one rule: never report a command as executed when it was not.

4. **Put expensive checks at boundaries, not on every edit**. Running an LLM audit or a warning banner on every single edit is costly, and repeated warnings quickly lose their force. Semantic checks (readability, consistency) belong to the pre-publication review gate (`skills/docs-maintenance/`). Machine-checkable ones (absolute-path leaks, secrets, Japanese docs lint) belong to the commit and push Git hooks. The one exception is deterministic, cheap lint, which also gives immediate feedback right after an edit (the textlint hook below). It is silent when there is nothing to report, so repetition does not wear it out.

## Layout

```text
.
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── README.ja.md
├── .textlintrc.json         # Japanese docs lint rules (used by pre-commit)
├── prh.yaml                 # terminology dictionary (grown from review findings)
├── docs/
│   ├── instruction-placement.md
│   ├── skill-authoring.md
│   └── policies/
│       ├── agent-collaboration.md
│       └── git-and-remote.md
├── git-hooks/
│   ├── pre-commit           # rejects environment-dependent absolute paths at commit time
│   └── pre-push             # scans for secrets with gitleaks before push (full history on first push)
├── skills/                  # each skill has SKILL.md and agents/openai.yaml
│   ├── ci-fix/
│   ├── debug-loop/
│   ├── dep-upgrade-safe/
│   ├── docs-maintenance/    # + references/documentation.md
│   ├── evaluation-loop/
│   ├── independent-review/  # + assets/REVIEW_PROMPT.md
│   ├── large-work/
│   ├── pair/                # + assets: 3 role briefs; references (transport-codex, design notes)
│   ├── pr-review-loop/
│   ├── semantic-generation/ # + references/referent-before-label.md
│   ├── ui-quality/          # + references (web, native, audit-rubric)
│   └── ui-verification/
├── templates/
│   ├── ACTIVE_PLAN.md
│   ├── PROJECT_AGENTS.md
│   ├── TASK.md
│   └── VERIFICATION.md
├── scripts/
│   ├── agent-check.example.sh
│   ├── textlint-hook.py     # Claude Code: instant lint right after a .md edit
│   └── validate-kit.py
└── tests/
    └── test_public_bundle.py
```

Each skill keeps the references and assets it needs inside its own directory, so nothing breaks when a skill is deployed on its own.

## Installation

If some of these files already exist on your machine, do not overwrite them; check their contents and symlink targets before switching. Replace `/absolute/path/to/common-agents` with the absolute path of your clone.

### Codex

Codex reads global instructions from `~/.codex/AGENTS.md` and user skills from `~/.agents/skills/`.

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

If you set `CODEX_HOME`, use that directory instead of `~/.codex`.

### Claude Code

Claude Code reads user instructions from `~/.claude/CLAUDE.md` and user skills from `~/.claude/skills/`. `CLAUDE.md` is a thin adapter that imports the `AGENTS.md` next to it.

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

These hooks are standard Git machinery, not an agent-only feature. They are in the kit as the last line of defense that holds agents and humans to the same rules. Set `git-hooks/` as the shared hooks directory via `core.hooksPath`:

```bash
git config --global core.hooksPath /absolute/path/to/agent-kit/git-hooks
```

- `pre-commit` rejects commits whose staged diff adds environment-dependent absolute paths (under the home directory or on external volumes).
- `pre-commit` then checks staged `.md` files with [textlint](https://textlint.org/), a Japanese technical-writing linter. It is on by default in every repository. A config at the repository root (`.textlintrc.json` etc.) takes precedence. Otherwise the kit's bundled `.textlintrc.json` (sentence length, redundant phrasing, kanji runs) and `prh.yaml` (terminology dictionary) apply. To opt a repository out, set `git config --local hooks.skipTextlint true`. Auto-fixable findings (terminology, number style) are applied to the working tree, but the commit still stops once. Machine fixes can overshoot, so a human reviews the diff, re-stages, and commits again.
<!-- textlint-disable prh -->（悪い例の引用のため、この区間だけ用語辞書の検査を除外 / prh is disabled for this quoted-example passage）
  The dictionary holds words reviewers actually flagged as hard on readers (e.g. 縮退 → フォールバック). Any word flagged in two or more reviews gets added, so the dictionary grows.
<!-- textlint-enable prh -->
  Where textlint is not installed, the hook only warns and lets the commit pass. Only rules that hold across all projects belong in the kit's bundled config and dictionary. To relax something for one project, use that repository's own root config (the precedence above). Enabling is a one-time step:

  ```bash
  npm install -g textlint textlint-rule-preset-ja-technical-writing \
    textlint-rule-prh textlint-filter-rule-comments
  ```

- `pre-push` scans the pushed commit range with gitleaks (all reachable history on the first push) and rejects the push when it finds likely secrets. Without gitleaks installed it only warns and lets the push through (`brew install gitleaks` to enable).
- When a repository has its own `.git/hooks/`, the shared hooks delegate to it after their own checks. Repositories that intentionally allow absolute paths set `git config --local hooks.allowLocalPaths true`.

### Instant lint on edit (Claude Code)

In Claude Code, textlint can run right after an agent edits or creates a `.md` file, so the agent fixes findings on the spot. Register the hook below in `~/.claude/settings.json`. It prints nothing when there are no findings. Agent-internal documents such as `_ai/` are excluded.

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

This registration is a manual step each user performs, like the `npm install` above. Commands that run automatically belong in settings a human writes for themselves, so this is not delegated to agents. Claude Code also does not auto-approve an agent writing this setting.

Codex has no equivalent hook mechanism; the Codex side is covered by pre-commit and the `$docs-maintenance` procedure.

### Personal environment policy

Machine-specific model locations, timezones, local logs, and path checks are not part of the public bundle. Users who need them create `~/.codex/local-policies/local-environment.md`. The shared `AGENTS.md` and `$large-work` read this file only when it exists.

## Applying to a project

1. Create a short project-specific `AGENTS.md` from `templates/PROJECT_AGENTS.md`.
2. Record the project's real build, lint, and test commands in the form of `templates/VERIFICATION.md`.
3. Write task acceptance criteria from `templates/TASK.md`, and working hypotheses and progress from `templates/ACTIVE_PLAN.md`.
4. Before adding anything to the shared rules, check the right location with `docs/instruction-placement.md`.

## Verification

```bash
python3 scripts/validate-kit.py
python3 -m unittest discover -s tests -v
```

The checks cover required files / skill frontmatter / reference targets / personal or machine-specific info / `AGENTS.md` size / the Claude adapter.

## Matching official docs

- [Codex: Custom instructions with AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md)
- [Codex: Build skills](https://developers.openai.com/codex/build-skills)
- [Claude Code: How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/slash-commands)

## Deliberately not shared

- A specific package manager, framework, or coding style
- Creating an issue for every bug or feature
- A specific review bot, workflow, or merge policy
- Publishing the full original user prompts
- Personal machines' absolute paths, caches, credentials, and local policies

These live in a project's `AGENTS.md`, lint and CI, personal settings, and private policies.

## License

MIT License (see `LICENSE`).
