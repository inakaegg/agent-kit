# AGENTS.md — <project name>

## Scope

このfileはこのrepository固有の指示だけを記載する。個人共通AGENTSを重複しない。

## Repository map

- Product specification: `<path>`
- Architecture / ADR: `<paths>`
- Verification: `<path>`
- Runbook: `<path>`
- Internal active task: `_ai/TASK.md`

## Project purpose

<このrepositoryが何を提供するかを1〜3文>

## Technology and established conventions

- Language/runtime:
- Package/build tool:
- Existing test runner:
- Formatter/linter:
- Supported platforms/versions:
- Follow existing patterns in:

projectが既に採用しているtool・styleを優先する。共通規則として別のpackage manager、framework、test layoutを持ち込まない。

## Canonical commands

| Purpose | Command |
|---|---|
| Setup | `<command>` |
| Fast check | `<command>` |
| Targeted test | `<command>` |
| Full check | `<command>` |
| Run app | `<command>` |
| UI/E2E | `<command>` |

実在しないplaceholderを残したまま運用しない。

## Architecture invariants

- ...

機械的に検出できるinvariantはlint、architecture test、type、CIでも強制する。

## Project-specific behavior

- ...

## Change-to-check matrix

- UI changes → `<UI command/artifact>`
- API/schema → `<contract/migration checks>`
- Audio/media → `<fixture/metric checks>`
- Performance → `<benchmark>`
- Security/auth → `<security tests/review>`

## Git / release differences

- Default branch:
- Branch/PR policy:
- Merge method:
- Release/deploy procedure:

## Nested instructions

- `<directory>/AGENTS.md` — <scope>
