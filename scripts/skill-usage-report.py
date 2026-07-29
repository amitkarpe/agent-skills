#!/usr/bin/env python3
"""Estimate Codex skill usage from local session and temp logs.

This is intentionally best-effort. It mines text artifacts for explicit skill
mentions and paths; it does not prove that a skill was actually selected by the
model in every case.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_ROOTS = [
    Path.home() / ".AGENTS-temp" / "agent-skills",
]


@dataclass
class SkillHit:
    count: int = 0
    files: Counter[str] = field(default_factory=Counter)
    repos: Counter[str] = field(default_factory=Counter)
    confidence: Counter[str] = field(default_factory=Counter)
    last_seen: str = ""


def skill_names(skill_root: Path) -> list[str]:
    names = []
    if not skill_root.exists():
        return names
    for child in sorted(skill_root.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            names.append(child.name)
    return names


def iter_files(roots: list[Path], since: datetime | None) -> list[Path]:
    out: list[Path] = []
    suffixes = {".jsonl", ".md", ".txt", ".log"}
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() not in suffixes:
                continue
            if since:
                try:
                    mtime = datetime.fromtimestamp(root.stat().st_mtime, timezone.utc)
                except OSError:
                    continue
                if mtime < since:
                    continue
            out.append(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            if since:
                try:
                    mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                except OSError:
                    continue
                if mtime < since:
                    continue
            out.append(path)
    return out


def repo_hint(path: Path) -> str:
    parts = path.parts
    if ".AGENTS-temp" in parts:
        idx = parts.index(".AGENTS-temp")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if "sessions" in parts or "archived_sessions" in parts:
        return "codex-session"
    return "unknown"


def mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def confidence_for(skill: str, text: str) -> str | None:
    escaped = re.escape(skill)
    high_patterns = [
        rf"/skills/{escaped}/SKILL\.md",
        rf"Using `{escaped}`",
        rf"Using {escaped}",
        rf"skill(?:s)?[:= ]+{escaped}",
        rf"\${escaped}\b",
    ]
    medium_patterns = [
        rf"/skills/{escaped}\b",
        rf"\b{escaped}\b",
    ]
    for pattern in high_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return "high"
    for pattern in medium_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return "medium"
    return None


def summarize(
    skill_root: Path,
    evidence_files: list[Path],
    max_file_bytes: int,
) -> dict[str, SkillHit]:
    names = skill_names(skill_root)
    hits = {name: SkillHit() for name in names}
    if not names:
        return hits
    name_re = re.compile("|".join(re.escape(name) for name in names), re.IGNORECASE)
    for path in evidence_files:
        try:
            if path.stat().st_size > max_file_bytes:
                text = path.read_text(errors="ignore")[:max_file_bytes]
            else:
                text = path.read_text(errors="ignore")
        except OSError:
            continue
        if not text:
            continue
        matched_names = {match.group(0).lower() for match in name_re.finditer(text)}
        if not matched_names:
            continue
        for name in names:
            if name.lower() not in matched_names:
                continue
            conf = confidence_for(name, text)
            if not conf:
                continue
            count = len(re.findall(re.escape(name), text, flags=re.IGNORECASE))
            count = max(count, 1)
            rel = str(path)
            hits[name].count += count
            hits[name].files[rel] += count
            hits[name].repos[repo_hint(path)] += count
            hits[name].confidence[conf] += 1
            seen = mtime_iso(path)
            if seen > hits[name].last_seen:
                hits[name].last_seen = seen
    return hits


def hit_confidence(hit: SkillHit) -> str:
    if hit.confidence["high"]:
        return "high"
    if hit.confidence["medium"]:
        return "medium"
    return "none"


def evidence_classification(hit: SkillHit) -> str:
    confidence = hit_confidence(hit)
    if confidence == "high":
        return "observed-active"
    if confidence == "medium":
        return "needs-review"
    return "not-observed"


def write_markdown(
    hits: dict[str, SkillHit],
    out: Path,
    roots: list[Path],
    days: int,
    evidence_files: list[Path],
) -> None:
    rows = []
    for name, hit in hits.items():
        if hit.count:
            rows.append((hit.count, name, hit))
    rows.sort(reverse=True)
    classifications = Counter(evidence_classification(hit) for hit in hits.values())
    root_text = ", ".join(f"`{root}`" for root in roots)
    window = f"last {days} days" if days > 0 else "all matching files"

    lines = [
        "# Skill Usage Report",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        f"Evidence roots: {root_text or '-'}",
        f"Window: {window}, based on file modification time.",
        f"Evidence files scanned: {len(evidence_files)}",
        "",
        "Method: best-effort text mining for explicit skill paths, use statements, and names.",
        "High-confidence evidence is classified as `observed-active`; name-only evidence is `needs-review`.",
        "`not-observed` means only that this bounded evidence set contained no match. It never permits deletion, archival, disabling, or unlinking.",
        "`situational` requires human review of the skill trigger and is not inferred from text counts.",
        "",
        "## Classification Summary",
        "",
        f"- `observed-active`: {classifications['observed-active']}",
        f"- `situational`: 0 (manual classification only)",
        f"- `not-observed`: {classifications['not-observed']}",
        f"- `needs-review`: {classifications['needs-review']}",
        "",
        "## Skills with Evidence",
        "",
        "| Skill | Classification | Estimated mentions | Confidence | Last seen | Top repos/lanes |",
        "|---|---|---:|---|---|---|",
    ]
    for count, name, hit in rows:
        repos = ", ".join(f"{repo} ({num})" for repo, num in hit.repos.most_common(4))
        lines.append(
            f"| `{name}` | {evidence_classification(hit)} | {count} | "
            f"{hit_confidence(hit)} | {hit.last_seen or '-'} | {repos or '-'} |"
        )

    not_observed = sorted(
        name for name, hit in hits.items() if evidence_classification(hit) == "not-observed"
    )
    lines.extend(
        [
            "",
            "## Not Observed in This Evidence Set",
            "",
            ", ".join(f"`{name}`" for name in not_observed) or "None.",
            "",
            "## Top Evidence Files",
            "",
        ]
    )
    for count, name, hit in rows[:25]:
        lines.append(f"### {name}")
        for file, num in hit.files.most_common(5):
            lines.append(f"- {num}: `{file}`")
        lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")


def write_json(hits: dict[str, SkillHit], out: Path) -> None:
    data = {}
    for name, hit in hits.items():
        data[name] = {
            "classification": evidence_classification(hit),
            "count": hit.count,
            "confidence": hit_confidence(hit),
            "last_seen": hit.last_seen,
            "repos": dict(hit.repos.most_common()),
            "top_files": dict(hit.files.most_common(20)),
        }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-root", type=Path, default=Path.cwd() / "skills")
    parser.add_argument("--root", type=Path, action="append", default=None)
    parser.add_argument("--out-md", type=Path, default=Path.home() / ".AGENTS-temp" / "agent-skills" / "usage" / "skill-usage-report.md")
    parser.add_argument("--out-json", type=Path, default=Path.home() / ".AGENTS-temp" / "agent-skills" / "usage" / "skill-usage-report.json")
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    parser.add_argument("--days", type=int, default=30, help="Only scan files modified in the last N days. Use 0 for all files.")
    args = parser.parse_args()

    roots = args.root or DEFAULT_ROOTS
    since = datetime.now(timezone.utc) - timedelta(days=args.days) if args.days > 0 else None
    evidence_files = iter_files(roots, since)
    hits = summarize(args.skill_root, evidence_files, args.max_file_bytes)
    write_markdown(hits, args.out_md, roots, args.days, evidence_files)
    write_json(hits, args.out_json)
    classifications = Counter(evidence_classification(hit) for hit in hits.values())
    print(
        f"observed_active={classifications['observed-active']} "
        f"needs_review={classifications['needs-review']} "
        f"not_observed={classifications['not-observed']} "
        f"report={args.out_md} json={args.out_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
