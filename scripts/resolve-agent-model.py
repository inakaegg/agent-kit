#!/usr/bin/env python3
"""Resolve a configured model to argv without invoking an LLM or evaluating env files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

MODEL_KEYS = (
    "REVIEW_MODEL_HEAVY", "REVIEW_MODEL_DEFAULT", "REVIEW_MODEL_READABILITY",
    "WRITING_MODEL_DEEP",
)
PROTECTED_KEYS = (*MODEL_KEYS, "REVIEW_REQUIRE_OTHER_LINEAGE")
EFFORTS = {
    "codex": {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"},
    "claude": {"low", "medium", "high", "xhigh", "max"},
}
CANDIDATE = re.compile(r"(codex|claude):([A-Za-z0-9][A-Za-z0-9._/-]*)\(([a-z]+)\)")
UNAVAILABLE_REASONS = {"authentication", "model-unavailable", "rate-limit"}
# Which CLI the calling session runs in. Claude Code exports CLAUDECODE to its children,
# Codex exports CODEX_THREAD_ID; a script run outside either sees neither.
PRIMARY_ENV = (("CODEX_THREAD_ID", "codex"), ("CLAUDECODE", "claude"))


class SettingsError(ValueError):
    pass


def read_settings(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if key not in PROTECTED_KEYS:
            continue
        if not separator:
            raise SettingsError(f"{path}:{number}: expected KEY=value")
        values[key] = value.strip()
    return values


def default_settings() -> Path:
    script = Path(__file__).resolve()
    # Symlink-installed skills retain the kit's live settings; exported skills use the bundle.
    for root in script.parents:
        if (root / "scripts/validate-kit.py").is_file() and (root / "agent-settings.env").is_file():
            return root / "agent-settings.env"
    bundled = script.parent.parent / "references/model-defaults.env"
    if bundled.is_file():
        return bundled
    raise SettingsError("No model settings found; provide --kit-settings")


def settings_for(defaults: Path, repo: Path) -> tuple[dict, dict]:
    if not defaults.is_file():
        raise SettingsError(f"Settings file does not exist: {defaults}")
    values, sources = {}, {}
    for path in (defaults, repo / "agent-settings.env"):
        for key, value in read_settings(path).items():
            values[key], sources[key] = value, str(path)
    local = repo / "agent-settings.local.env"
    for key, value in read_settings(local).items():
        if value != values.get(key):
            raise SettingsError(f"{local}: {key} must be changed in tracked agent-settings.env")
    return values, sources


def parse_candidate(value: str) -> tuple[str, str, str]:
    match = CANDIDATE.fullmatch(value)
    if not match:
        raise SettingsError(f"Ambiguous or invalid candidate {value!r}; use CLI:MODEL(EFFORT)")
    cli, model, effort = match.groups()
    if effort not in EFFORTS[cli]:
        raise SettingsError(f"Unsupported {cli} effort: {effort}")
    return cli, model, effort


def unavailable_candidates(entries: list[str]) -> dict[str, str]:
    unavailable = {}
    for entry in entries:
        candidate, separator, reason = entry.partition("=")
        parse_candidate(candidate)
        if not separator or reason not in UNAVAILABLE_REASONS:
            raise SettingsError("--unavailable requires CANDIDATE=authentication|model-unavailable|rate-limit")
        unavailable[candidate] = reason
    return unavailable


def detect_primary_cli(environ=os.environ) -> str | None:
    """The CLI this process runs in, or None when it cannot be told.

    Both variables set means a nested launch (one CLI started from the other); the inner one
    cannot be told from the outer, so no CLI is preferred and the configured order stands
    unless --primary-cli says otherwise."""
    found = [cli for variable, cli in PRIMARY_ENV if environ.get(variable)]
    return found[0] if len(found) == 1 else None


def select(values: dict, sources: dict, key: str, unavailable: dict, binaries: dict,
           implementer_cli: str | None = None, primary_cli: str | None = None) -> dict:
    candidates = values.get(key, "").split()
    if not candidates:
        raise SettingsError(f"{key} is empty or missing")
    parsed = [(candidate, parse_candidate(candidate)) for candidate in dict.fromkeys(candidates)]
    lineage = values.get("REVIEW_REQUIRE_OTHER_LINEAGE", "true")
    if lineage not in {"true", "false"}:
        raise SettingsError("REVIEW_REQUIRE_OTHER_LINEAGE must be true or false")
    require_other = key == "REVIEW_MODEL_HEAVY" and lineage == "true"
    if require_other and implementer_cli is None:
        raise SettingsError("This heavy review requires --implementer-cli to enforce other lineage")
    if any(candidate not in candidates for candidate in unavailable):
        raise SettingsError("--unavailable names a candidate outside this role's configured list")
    skipped = []
    ordered, ordering = parsed, "configured"
    if require_other:
        ordering = "other-lineage"
        # Heavy-risk review: the other lineage comes first whatever CLI the caller runs in.
        ordered = [p for p in parsed if p[1][0] != implementer_cli] + [p for p in parsed if p[1][0] == implementer_cli]
    elif primary_cli:
        ordering = "primary-cli"
        # Everything else follows the caller's CLI, so the session's own plan is used first;
        # the configured order still decides within each CLI.
        ordered = [p for p in parsed if p[1][0] == primary_cli] + [p for p in parsed if p[1][0] != primary_cli]
    for candidate, (cli, model, effort) in ordered:
        if candidate in unavailable:
            skipped.append({"candidate": candidate, "reason": unavailable[candidate]})
            continue
        executable = shutil.which(binaries.get(cli) or cli)
        if executable is None:
            skipped.append({"candidate": candidate, "reason": "missing-cli"})
            continue
        if cli == "codex":
            argv = [executable, "exec", "--ignore-user-config", "--ephemeral", "-m", model,
                    "-c", "model_reasoning_effort=" + json.dumps(effort)]
            if key.startswith("REVIEW_"):
                # A reviewer must not edit and must not receive the implementer's workflow:
                # --ignore-user-config leaves already-trusted $CODEX_HOME hooks active, so
                # the hooks feature is switched off explicitly.
                argv += ["-s", "read-only", "--disable", "hooks"]
            else:
                # A writer selected through WRITING_MODEL_DEEP has to edit the document; with the
                # user config ignored the default sandbox would be read-only.
                argv += ["-s", "workspace-write"]
        else:
            argv = [executable, "-p", "--model", model, "--effort", effort,
                    "--setting-sources", "", "--disable-slash-commands", "--no-session-persistence"]
        return {"status": "selected", "key": key, "source": sources[key], "candidate": candidate,
                "cli": cli, "model": model, "effort": effort, "argv": argv, "skipped": skipped,
                "require_other_lineage": require_other, "primary_cli": primary_cli,
                "ordering": ordering, "provisional": require_other and cli == implementer_cli}
    return {"status": "unavailable", "key": key, "source": sources[key], "skipped": skipped,
            "require_other_lineage": require_other, "primary_cli": primary_cli, "ordering": ordering}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", choices=MODEL_KEYS, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root or linked worktree root")
    parser.add_argument("--kit-settings", type=Path)
    parser.add_argument("--codex-bin")
    parser.add_argument("--claude-bin")
    parser.add_argument("--implementer-cli", choices=("codex", "claude"))
    parser.add_argument("--primary-cli", choices=("codex", "claude"),
                        help="CLI whose candidates are tried first (default: the CLI this session runs in, "
                             "detected from CODEX_THREAD_ID / CLAUDECODE; heavy reviews with "
                             "REVIEW_REQUIRE_OTHER_LINEAGE=true still put the other lineage first)")
    parser.add_argument("--unavailable", action="append", default=[], metavar="CANDIDATE=REASON")
    args = parser.parse_args()
    try:
        values, sources = settings_for(args.kit_settings or default_settings(), args.repo.resolve())
        result = select(values, sources, args.key, unavailable_candidates(args.unavailable),
                        {"codex": args.codex_bin, "claude": args.claude_bin}, args.implementer_cli,
                        args.primary_cli or detect_primary_cli())
    except (SettingsError, OSError) as error:
        print(json.dumps({"status": "invalid-settings", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "selected" else 1


if __name__ == "__main__":
    sys.exit(main())
