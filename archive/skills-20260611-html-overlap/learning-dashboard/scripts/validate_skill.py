#!/usr/bin/env python3
"""Validate the learning-dashboard skill package structure."""
from __future__ import annotations
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md",
    "references/design.md",
    "references/component-library.md",
    "references/output-modes.md",
    "references/devops-aws.md",
    "references/quality-gate.md",
    "assets/midnight-dashboard-template.html",
    "agents/openai.yaml",
]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    for item in REQUIRED:
        if not (ROOT / item).exists():
            return fail(f"missing {item}")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\n"):
        return fail("SKILL.md missing YAML frontmatter")
    if "name: learning-dashboard" not in skill:
        return fail("SKILL.md missing expected name")
    if "description:" not in skill:
        return fail("SKILL.md missing description")
    template = (ROOT / "assets/midnight-dashboard-template.html").read_text(encoding="utf-8")
    for needle in ["<!doctype html>", "sticky-nav", "tab-button", "details", "@media print"]:
        if needle not in template:
            return fail(f"template missing {needle}")
    if re.search(r"https?://", template):
        return fail("template should not require remote assets")
    print("OK: learning-dashboard skill structure valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
