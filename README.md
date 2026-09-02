# agent-kit — an operations kit for AI coding agents

🇯🇵 日本語ドキュメント: [README.ja.md](README.ja.md)

A set of working rules (`AGENTS.md`), task-specific playbooks (skills), templates, and verification scripts shared by Codex and Claude Code. This is not a generic boilerplate: it is the setup I actually run for solo development, frozen as is (opinionated by design).

Agents always load only the 160-line `AGENTS.md`. Detailed procedures live in skills. Task acceptance criteria, working hypotheses, and durable specs live in separate files (see `templates/`). Machine-checkable rules live in verification scripts. The kit's job is to keep permission boundaries and stop conditions identical across Codex and Claude Code on every project. Push, publication, and billing always require explicit human approval.

## Design principles

1. **Enforce rules with machines, not documents**. Rules that exist only in a policy document get followed inconsistently. So the policy document stays a thin entry point. The real enforcement is checks that fail when a rule is broken: `scripts/validate-kit.py`, the pre-commit and pre-push hooks in `git-hooks/`, and tests. When written reminders about the same rule keep accumulating, the rule moves into lint / tests / hooks / CI. The placement procedure is `docs/instruction-placement.md`.

2. **Fully autonomous loops are only for closed tasks with machine-checkable success**. Except for work whose "done" can be judged by tests or numbers — bulk migrations, lint sweeps — agents are not run unattended. Most software development surfaces unclear points mid-build, and the spec settles through questions and decisions. So the default is a supervised pair setup: implementer plus watcher across two sessions (the [pair-watch](https://github.com/inakaegg/pair-watch) plugin). Extend the autonomous stretch, but return to a human exactly at the real decision points.

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
├── agent-settings.env       # default values for the settings toggles (AGENTS.md §1)
├── prh.yaml                 # terminology dictionary (grown from review findings)
├── docs/
│   ├── instruction-placement.md
│   ├── skill-authoring.md
│   └── policies/
│       └── git-and-remote.md
├── git-hooks/
│   ├── commit-msg           # enforces the "English / Japanese" subject-line order
│   ├── pre-commit           # checks branch, secrets, environment-dependent paths, Japanese lint, doc links at commit time
│   └── pre-push             # scans for secrets with gitleaks before push (full history on first push)
├── skills/                  # each skill has SKILL.md and agents/openai.yaml
│   ├── architecture-diagram/ # + assets/diagram_template.py, references/pitfalls.md
│   ├── ci-fix/
│   ├── debug-loop/
│   ├── dep-upgrade-safe/
│   ├── docs-maintenance/    # + references/documentation.md
│   ├── evaluation-loop/
│   ├── independent-review/  # + assets/REVIEW_PROMPT.md
│   ├── large-work/
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
│   ├── agent-check.sh       # the kit's own checks (validate-kit + tests), run by pre-push and CI
│   ├── git-guard-hook.py    # Claude Code: blocks --no-verify and git add . in agent commands
│   ├── textlint-hook.py     # Claude Code: instant lint right after a .md edit
│   └── validate-kit.py
└── tests/
    ├── test_commit_guards.py
    ├── test_git_guard_hook.py
    ├── test_pre_push_hook.py
    ├── test_public_bundle.py
    └── test_textlint_hook.py
```

Each skill keeps the references and assets it needs inside its own directory, so nothing breaks when a skill is deployed on its own.

Skill bodies, references, and assets are written in Japanese on purpose: this is the kit its author runs every day, and it is verified in that form. What is English-first is the outward-facing layer — the `description` front matter that decides whether a skill fires (Japanese trigger cues kept alongside it), the Codex-side `agents/openai.yaml` metadata, this README, and the subject line of new commits (earlier history is left as it is).

The two-seat setup (implementer plus watcher) is not bundled in this kit; it is published as the standalone [pair-watch](https://github.com/inakaegg/pair-watch) plugin (installable from its Claude Code plugin marketplace), with the skill body translated into English as well. That plugin is the single source for this workflow.

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

The two-seat setup (`$pair-watch`) is not under `skills/`, so the symlinks above do not install it. Add it as a Claude Code plugin:

```text
/plugin marketplace add https://github.com/inakaegg/pair-watch
/plugin install pair-watch@pair-watch
```

### Git hooks

These hooks are standard Git machinery, not an agent-only feature. They are in the kit as the last line of defense that holds agents and humans to the same rules. Set `git-hooks/` as the shared hooks directory via `core.hooksPath`. The command below sets it only when it is not set yet; if it is already set, it prints the current value and changes nothing:

```bash
git config --global core.hooksPath \
  || git config --global core.hooksPath /absolute/path/to/agent-kit/git-hooks
```

If `core.hooksPath` already points to your own hooks directory, do not overwrite it. Either merge the kit's hooks into that directory, or choose which to use per repository with `git config --local core.hooksPath`. Repositories with plain `.git/hooks/` need nothing: the kit's hooks delegate to them after their own checks. To remove the kit, run `git config --global --unset core.hooksPath` **before** deleting the directory — deleting first leaves every repository silently running no hooks.

- `pre-commit` first rejects commits on a detached HEAD, so a commit never lands on an unintended history line just because nobody checked the current branch (the mechanical form of the "check the branch before committing" rule). Rebase and `git am` runs are exempt. To allow detached-HEAD commits in one repository, set `git config --local hooks.allowDetachedHead true`.
- `pre-commit` also rejects non-document commits on `main` / `master`: when the staged files include anything other than documents, the commit stops with a pointer to the task-branch rule (behavior changes go on a task branch and worktree; document-only commits stay allowed on main). "Documents" means `.md` files plus the globs in the `MAIN_GUARD_EXTRA_DOCS` setting — by default dotfiles (`.*`) such as `.gitignore`, so repo-config files pass too. Concluding a merge (`MERGE_HEAD` present) is exempt, since merges into main are an explicitly approved operation. To opt a repository out where committing straight to main is the norm, set `git config --local hooks.allowMainCommits true` or `MAIN_DOC_GUARD=false` in agent-settings (below).
- `pre-commit` also rejects commits that cancel unpushed history — deleting a file that an unpushed commit added, or reverting a file back to its upstream content — and asks for a squash (`git reset --soft`) instead, the mechanical form of the "squash same-purpose fixups before pushing" rule. A leftover cancel pair would also carry anything gitleaks rules missed into pushed history. `pre-push` backs this up for cancellations only visible across the whole pushed range (multi-commit net-zero, commits made by another session). `pre-commit` skips branches without an upstream, having no base to compare against. First pushes are not exempt: `pre-push` scans everything being sent — the commits unreachable from the remote's tracking refs, or the whole reachable history in a repository that has no tracking refs yet — and blocks paths added and then deleted inside it. To keep a cancel pair on purpose (a recorded experiment), set `git config --local hooks.allowNetZeroHistory true`. Only the repository-level setting is read: a global entry does not lift the guard, so the exemption cannot be turned on for every repository at once. How strict the guard is comes from `SQUASH_GUARD` in agent-settings (below): `true` stops the commit or push, `warn` prints the same findings and continues, `false` disables it. **The default is `warn`**; a repository that has confirmed there are no false positives sets `true` in its own `agent-settings.env` to make it stop. Known limits: an `--amend` that removes the cancellation is indistinguishable from a new commit and is blocked the same way (use `git reset --soft`); renames are counted as an addition plus a deletion, so `git mv` on a file added within the range is blocked as a cancellation too; and ranges containing merge commits are not scanned.
- `pre-commit` then scans the staged content with gitleaks and rejects the commit when it finds likely secrets. gitleaks is required: without it installed the commit itself is stopped (`brew install gitleaks`; suppress false positives via `.gitleaksignore`).
- `pre-commit` rejects commits whose staged diff adds environment-dependent absolute paths (under the home directory or on external volumes).
- `pre-commit` then checks staged `.md` files with [textlint](https://textlint.org/), a Japanese technical-writing linter. It is on by default in every repository. A config at the repository root (`.textlintrc.json` etc.) takes precedence. Otherwise the kit's bundled `.textlintrc.json` (sentence length, redundant phrasing, kanji runs) and `prh.yaml` (terminology dictionary) apply. To opt a repository out, set `git config --local hooks.skipTextlint true` or `TEXTLINT=false` in agent-settings (below). Auto-fixable findings (terminology, number style) are applied to the working tree, but the commit still stops once. Machine fixes can overshoot, so a human reviews the diff, re-stages, and commits again.
<!-- textlint-disable prh -->（悪い例の引用のため、この区間だけ用語辞書の検査を除外 / prh is disabled for this quoted-example passage）
  The dictionary holds words reviewers actually flagged as hard on readers (e.g. 縮退 → フォールバック). Any word flagged in two or more reviews gets added, so the dictionary grows.
<!-- textlint-enable prh -->
  Where textlint is not installed, the hook only warns and lets the commit pass. Only rules that hold across all projects belong in the kit's bundled config and dictionary. To relax something for one project, use that repository's own root config (the precedence above). Enabling is a one-time step:

  ```bash
  npm install -g textlint textlint-rule-preset-ja-technical-writing \
    textlint-rule-prh textlint-filter-rule-comments
  ```

- `pre-commit` also checks relative links in staged `.md` files and rejects the commit when a link target does not exist. It is a deterministic file-existence check (no LLM, a few milliseconds); external URLs, in-page anchors, absolute paths, and links inside code fences are ignored. Where perl is not available the check is skipped. To opt a repository out, set `git config --local hooks.skipLinkCheck true` or `LINKCHECK=false` in agent-settings (below).
- `commit-msg` checks the subject line's language order. When the subject contains Japanese, it must be a one-liner in the order `COMMIT_LANG_ORDER` names (`docs/policies/git-and-remote.md`): `en-ja` for "English summary / Japanese summary" (the default), `ja-en` for the reverse, `off` to skip the check. English-only subjects are not checked, and neither are merge / revert / fixup subjects or messages replayed by rebase or cherry-pick. Set the key in the repository's `agent-settings.env` so the choice is committed with the repository; `git config --local hooks.skipSubjectLang true` still works for the same opt-out.
- `commit-msg` also checks the body's languages with the same `COMMIT_LANG_ORDER` key. When the subject contains Japanese and the message has a body, the body must carry both an English and a Japanese explanation in that order. Body-less commits are not checked, and the trailing trailer block (`Co-Authored-By:` etc.) and separator lines do not count as body. `git config --local hooks.skipBodyLang true` is the same opt-out.
- `pre-push` scans the pushed commit range with gitleaks (all reachable history on the first push) and rejects the push when it finds likely secrets. Without gitleaks installed it only warns and lets the push through (`brew install gitleaks` to enable).
- `pre-push` then runs `scripts/agent-check.sh fast` and rejects the push when it fails. This is opt-in per repository: `git config --local hooks.runAgentCheck true`. The script collects the project's verification commands (see `templates/VERIFICATION.md`). Opt-in is deliberate: this hook applies to every repository on the machine. A script inside a cloned third-party repository must not run just because you pushed.
- When a repository has its own `.git/hooks/`, the shared hooks delegate to it after their own checks. Repositories that intentionally allow absolute paths set `git config --local hooks.allowLocalPaths true`.

### Settings toggles (agent-settings)

Some rules — the hook checks above and a few working rules in `AGENTS.md` and `CLAUDE.md` (auto commit, worktree requirement, reviews and which models review or write, CLI-first) — can be switched per repository through `agent-settings.env`. Model duties are plain values (`REVIEW_MODEL_*`, `WRITING_MODEL_DEEP`), so usage limits or new models are handled by changing a setting, not by editing the rule documents. Resolution is three layers, later wins: the kit's `agent-settings.env` (defaults) → `agent-settings.env` at the work repository's root → `agent-settings.local.env` there (untracked; add it to the repository's `.gitignore`; use it for personal or temporary switches — except loosening the five model-duty keys (`REVIEW_MODEL_*`, `REVIEW_REQUIRE_OTHER_LINEAGE`, `WRITING_MODEL_DEEP`), which must stay in a tracked env file for traceability). The format is plain `KEY=value` lines, read line by line (never sourced as shell), so values may contain spaces and parentheses. The keys and their defaults live in the kit's `agent-settings.env` (commented); each toggleable rule in `AGENTS.md` (or `CLAUDE.md`, for Claude Code specific ones) names its key inline, and the resolution mechanism is defined in `AGENTS.md` §1. Permission boundaries and the evidence rules (e.g. the `--no-verify` ban) are deliberately not toggleable, with one exception: `AUTO_MERGE_PRIVATE`, on by default, lets an agent merge a fully reviewed task branch into the default branch of a private repository you do not share, without asking each time. Push and PR creation still require permission, and adding another such exception needs your confirmation (`AGENTS.md` §1).

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

### Agent git guard (Claude Code)

Two rules in `AGENTS.md` have no enforcement point on the git side: the ban on `--no-verify` (a hook cannot prevent its own bypass) and the ban on `git add .` / `-A` / `--all` (git has no hook for staging). `scripts/git-guard-hook.py` closes both for Claude Code by inspecting each Bash command the agent is about to run and blocking the forbidden forms before they execute. It binds only the agent's tool calls; a human typing the same commands in a terminal is unaffected. Register it in `~/.claude/settings.json` (the same manual-registration principle as above applies):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/agent-kit/scripts/git-guard-hook.py"
          }
        ]
      }
    ]
  }
}
```

Codex has no equivalent pre-execution hook; on the Codex side these two rules remain document-enforced (`AGENTS.md` §5 / §8).

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
