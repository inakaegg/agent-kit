#!/usr/bin/env python3
"""Validate the common agent instruction kit without external dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs/instruction-placement.md",
    "docs/policies/git-and-remote.md",
    "templates/TASK.md",
    "templates/ACTIVE_PLAN.md",
    "templates/PROJECT_AGENTS.md",
    "templates/VERIFICATION.md",
    "skills/docs-maintenance/references/documentation.md",
    "skills/independent-review/assets/REVIEW_PROMPT.md",
    "tests/test_public_bundle.py",
]

EXPECTED_SKILLS = {
    "pair",
    "debug-loop",
    "evaluation-loop",
    "large-work",
    "ui-verification",
    "independent-review",
    "pr-review-loop",
    "docs-maintenance",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"missing YAML frontmatter: {path.relative_to(ROOT)}")
    try:
        block = text.split("---\n", 2)[1]
    except IndexError:
        fail(f"invalid YAML frontmatter: {path.relative_to(ROOT)}")
    values: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def validate_required_files() -> None:
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}")


def validate_agents_size() -> None:
    lines = (ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    if len(lines) > 160:
        fail(f"AGENTS.md is too long: {len(lines)} lines (limit: 160)")
    if len(lines) < 60:
        fail(f"AGENTS.md is unexpectedly short: {len(lines)} lines")


def validate_skills() -> None:
    found: set[str] = set()
    for skill_file in sorted((ROOT / "skills").glob("*/SKILL.md")):
        data = parse_frontmatter(skill_file)
        name = data.get("name")
        description = data.get("description")
        directory_name = skill_file.parent.name
        if name != directory_name:
            fail(
                f"skill name mismatch: {skill_file.relative_to(ROOT)} "
                f"has name={name!r}, expected {directory_name!r}"
            )
        if not description:
            fail(f"skill has no description: {skill_file.relative_to(ROOT)}")
        if not (skill_file.parent / "agents" / "openai.yaml").is_file():
            fail(f"skill has no agents/openai.yaml: {skill_file.relative_to(ROOT)}")
        found.add(directory_name)
    if found != EXPECTED_SKILLS:
        fail(f"unexpected skill set: found={sorted(found)}, expected={sorted(EXPECTED_SKILLS)}")


def validate_agents_references() -> None:
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if re.search(r"`skills/[^`]+", agents_text):
        fail("AGENTS.md contains an install-layout-dependent Skill path")
    for skill_name in sorted(EXPECTED_SKILLS):
        if f"`${skill_name}`" not in agents_text:
            fail(f"AGENTS.md does not reference Skill by name: {skill_name}")
    required_paths = {
        "~/.codex/agent-kit/docs/policies/git-and-remote.md",
        "~/.codex/agent-kit/templates/TASK.md",
        "~/.codex/agent-kit/docs/instruction-placement.md",
        "~/.codex/local-policies/local-environment.md",
    }
    for reference in sorted(required_paths):
        if f"`{reference}`" not in agents_text:
            fail(f"AGENTS.md is missing explicit policy path: {reference}")


def validate_claude_adapter() -> None:
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if "@AGENTS.md" not in text:
        fail("CLAUDE.md does not import @AGENTS.md")
    if text.count("@AGENTS.md") != 1:
        fail("CLAUDE.md should import @AGENTS.md exactly once")


def validate_no_private_source_copy() -> None:
    patterns = {
        "private key": re.compile(r"BEGIN\s+PRIVATE\s+KEY"),
        "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        "GitHub token": re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
        "user home path": re.compile(r"/" r"Users/[^/\s]+"),
        "external volume path": re.compile(r"/" r"Volumes/"),
        "personal handle": re.compile(r"\b" + "inaka" + r"egg\b", re.IGNORECASE),
        "personal account number": re.compile(r"\b" + "5237" + r"6271\b"),
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {
            ".md",
            ".py",
            ".sh",
            ".yaml",
            ".yml",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in patterns.items():
            if pattern.search(text):
                fail(f"possible {label} in {path.relative_to(ROOT)}")


def validate_verification_source() -> None:
    duplicate = ROOT / "docs" / "quality" / "verification.md"
    if duplicate.exists():
        fail("duplicate verification source exists: docs/quality/verification.md")


def main() -> None:
    validate_required_files()
    validate_agents_size()
    validate_skills()
    validate_agents_references()
    validate_claude_adapter()
    validate_no_private_source_copy()
    validate_verification_source()
    print("PASS: common agent kit is structurally valid")


if __name__ == "__main__":
    main()
