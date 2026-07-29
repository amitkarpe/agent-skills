#!/usr/bin/env python3
"""Report skill exposure, description length, tier, and recommendation."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TIERS = {
    "safe-shell-ops": "global-core",
    "amit-operator-commands": "global-core",
    "prepare-worker-goal": "global-core",
    "run-worker-goal": "global-core",
    "web-html-page": "global-core",
    "visual-explainer": "global-core",
    "deep-work": "global-core",
    "repo-summary-and-relation-mapping": "global-core",
    "aws-private-network-preflight": "aws-daily",
    "aws-ssm-run-command": "aws-daily",
    "ssm-command-evidence": "aws-daily",
    "ami-validation-ssm": "situational",
    "imagebuilder-component-publish": "explicit-guarded",
    "imagebuilder-bake-validate": "aws-daily",
    "s3-artifact-stage-verify": "situational",
    "cis-inspector-scan": "aws-daily",
    "cis-ssm-apply-validate": "explicit-guarded",
    "ssm-patch-quicksetup-prod": "explicit-guarded",
    "ec2-quick-create": "aws-daily",
    "ec2-ttl-alert": "situational",
    "ecs-cluster-health-review": "situational",
    "ecs-mixed-ami-canary": "situational",
    "ecs-monitoring": "aws-daily",
    "ecs-recovery": "aws-daily",
    "awslogs-investigation": "situational",
    "gitlab-triage": "repo-scoped",
    "nessus-cis-csv-analysis": "repo-scoped",
    "chatgpt-browser-oracle": "installed-disabled/call-by-name",
    "linux-backup-to-s3": "installed-disabled/call-by-name",
    "skill-autoresearch-loop": "installed-disabled/call-by-name",
}

TEST_CONTRACTS = {
    "ami-validation-ssm/tests/smoke-test.sh": "launcher syntax and help contract",
    "aws-architecture-diagram/scripts/self_test.sh": "end-to-end diagram build, validation, render, and review",
    "aws-architecture-diagram/scripts/test_v24.py": "accessible metadata and non-mutating clearance validation",
    "cis-ssm-apply-validate/tests/smoke-test.sh": "validation evidence, isolation, and dry-run workflow",
    "cis-ssm-apply-validate/tests/test.sh": "input, schema, required-flag, and output-directory rejection",
    "imagebuilder-component-publish/tests/smoke-test.sh": "publisher syntax and help contract",
    "skill-autoresearch-loop/tests/smoke-test.sh": "deterministic autoresearch workspace scaffolding",
    "va-report-review/tests/test_review.py": "source parsing, filtering, escaping, comparison, and failure contracts",
}


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    description: str
    active: bool
    active_path: str
    tier: str
    recommendation: str


@dataclass(frozen=True)
class TestArtifact:
    skill: str
    path: str
    kind: str
    runnable: bool
    protected_contract: str


def parse_front_matter(skill_file: Path) -> dict[str, str]:
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            value = match.group(2).strip().strip('"').strip("'")
            metadata[match.group(1)] = value
    return metadata


def active_target(dest_root: Path, name: str) -> tuple[bool, str]:
    dest = dest_root / name
    if not dest.exists() and not dest.is_symlink():
        return False, ""
    if dest.is_symlink():
        try:
            return True, str(dest.resolve(strict=False))
        except OSError:
            return True, "broken symlink"
    return True, "non-symlink"


def recommendation(name: str, tier: str, active: bool, desc_len: int) -> str:
    if tier == "global-core":
        return "keep globally active" if active else "consider linking globally"
    if tier == "aws-daily":
        return "keep for normal AWS profile"
    if tier == "situational":
        return "enable only for matching lane"
    if tier == "explicit-guarded":
        return "keep separate; consider explicit-only policy"
    if tier == "installed-disabled/call-by-name":
        return "install only when needed or call explicitly"
    if desc_len > 260:
        return "shorten description; keep trigger words first"
    return "repo/profile scoped"


def collect(skills_root: Path, dest_root: Path) -> list[Skill]:
    skills: list[Skill] = []
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        meta = parse_front_matter(skill_file)
        name = meta.get("name", skill_dir.name)
        desc = meta.get("description", "")
        active, target = active_target(dest_root, name)
        tier = DEFAULT_TIERS.get(name, "repo-scoped")
        skills.append(
            Skill(
                name=name,
                path=skill_dir,
                description=desc,
                active=active,
                active_path=target,
                tier=tier,
                recommendation=recommendation(name, tier, active, len(desc)),
            )
        )
    return skills


def count_dest_entries(dest_root: Path) -> int:
    if not dest_root.is_dir():
        return 0
    return sum(1 for path in dest_root.iterdir() if path.name != ".system")


def artifact_kind(relative: Path) -> str | None:
    parts = relative.parts
    if "fixtures" in parts:
        return "fixture"
    if "examples" in parts:
        return "example"
    name = relative.name.lower()
    if relative.suffix.lower() in {".sh", ".py", ".js", ".ts"} and (
        "tests" in parts
        or name.startswith(("test_", "test-", "self_test", "self-test", "smoke_test", "smoke-test"))
    ):
        return "test"
    return None


def collect_test_artifacts(skills_root: Path) -> list[TestArtifact]:
    artifacts: list[TestArtifact] = []
    for path in sorted(item for item in skills_root.rglob("*") if item.is_file()):
        relative = path.relative_to(skills_root)
        kind = artifact_kind(relative)
        if not kind:
            continue
        relative_text = relative.as_posix()
        artifacts.append(
            TestArtifact(
                skill=relative.parts[0],
                path=relative_text,
                kind=kind,
                runnable=kind == "test",
                protected_contract=TEST_CONTRACTS.get(relative_text, "review required") if kind == "test" else "-",
            )
        )
    return artifacts


def print_table(skills: list[Skill]) -> None:
    rows = [["skill", "desc_len", "active", "tier", "recommendation"]]
    for skill in skills:
        rows.append([
            skill.name,
            str(len(skill.description)),
            "yes" if skill.active else "no",
            skill.tier,
            skill.recommendation,
        ])
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for index, row in enumerate(rows):
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))
        if index == 0:
            print("  ".join("-" * width for width in widths))


def print_markdown(skills: list[Skill]) -> None:
    print("| skill | desc_len | active | tier | recommendation |")
    print("| --- | ---: | :---: | --- | --- |")
    for skill in skills:
        active = "yes" if skill.active else "no"
        print(f"| `{skill.name}` | {len(skill.description)} | {active} | {skill.tier} | {skill.recommendation} |")


def print_csv(skills: list[Skill]) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(["skill", "description_length", "active", "active_path", "tier", "recommendation"])
    for skill in skills:
        writer.writerow([skill.name, len(skill.description), skill.active, skill.active_path, skill.tier, skill.recommendation])


def print_test_table(artifacts: list[TestArtifact]) -> None:
    rows = [["kind", "skill", "runnable", "path", "protected contract"]]
    for artifact in artifacts:
        rows.append([
            artifact.kind,
            artifact.skill,
            "yes" if artifact.runnable else "no",
            artifact.path,
            artifact.protected_contract,
        ])
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    for index, row in enumerate(rows):
        print("  ".join(value.ljust(widths[column]) for column, value in enumerate(row)))
        if index == 0:
            print("  ".join("-" * width for width in widths))


def print_test_markdown(artifacts: list[TestArtifact]) -> None:
    print("| kind | skill | runnable | path | protected contract |")
    print("| --- | --- | :---: | --- | --- |")
    for artifact in artifacts:
        runnable = "yes" if artifact.runnable else "no"
        print(
            f"| {artifact.kind} | `{artifact.skill}` | {runnable} | "
            f"`{artifact.path}` | {artifact.protected_contract} |"
        )


def print_test_csv(artifacts: list[TestArtifact]) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(["kind", "skill", "runnable", "path", "protected_contract"])
    for artifact in artifacts:
        writer.writerow([
            artifact.kind,
            artifact.skill,
            artifact.runnable,
            artifact.path,
            artifact.protected_contract,
        ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", default="skills")
    parser.add_argument("--dest-root", default=str(Path.home() / ".codex" / "skills"))
    parser.add_argument("--format", choices=["table", "md", "csv"], default="table")
    parser.add_argument("--tests", action="store_true", help="Inventory test programs, fixtures, and examples")
    args = parser.parse_args()

    skills_root = Path(args.skills_root).expanduser().resolve()
    dest_root = Path(args.dest_root).expanduser()
    if not skills_root.is_dir():
        raise SystemExit(f"skills root not found: {skills_root}")

    if args.tests:
        artifacts = collect_test_artifacts(skills_root)
        counts = {kind: sum(1 for item in artifacts if item.kind == kind) for kind in ("test", "fixture", "example")}
        unmapped = sum(
            1 for item in artifacts if item.kind == "test" and item.protected_contract == "review required"
        )
        print(
            f"test_programs={counts['test']} fixtures={counts['fixture']} "
            f"examples={counts['example']} unmapped_contracts={unmapped}"
        )
        if args.format == "table":
            print_test_table(artifacts)
        elif args.format == "md":
            print_test_markdown(artifacts)
        else:
            print_test_csv(artifacts)
        return 0

    skills = collect(skills_root, dest_root)
    active_count = sum(1 for skill in skills if skill.active)
    total_active = count_dest_entries(dest_root)
    print(f"skills={len(skills)} active_total={total_active} active_source_owned={active_count} dest_root={dest_root}")
    if args.format == "table":
        print_table(skills)
    elif args.format == "md":
        print_markdown(skills)
    else:
        print_csv(skills)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
