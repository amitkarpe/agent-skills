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


def summarize(skill_root: Path, roots: list[Path], max_file_bytes: int, days: int) -> dict[str, SkillHit]:
    names = skill_names(skill_root)
    hits = {name: SkillHit() for name in names}
    if not names:
        return hits
    name_re = re.compile("|".join(re.escape(name) for name in names), re.IGNORECASE)
    since = datetime.now(timezone.utc) - timedelta(days=days) if days > 0 else None
    for path in iter_files(roots, since):
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


def write_markdown(hits: dict[str, SkillHit], out: Path) -> None:
    rows = []
    for name, hit in hits.items():
        if hit.count:
            rows.append((hit.count, name, hit))
    rows.sort(reverse=True)

    lines = [
        "# Skill Usage Report",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "Method: best-effort log mining from recent ~/.AGENTS-temp/agent-skills files.",
        "Confidence is high when explicit SKILL.md paths or use statements are found; medium when only skill names are mentioned.",
        "",
        "## Summary",
        "",
        "| Skill | Estimated mentions | Confidence | Last seen | Top repos/lanes |",
        "|---|---:|---|---|---|",
    ]
    for count, name, hit in rows:
        repos = ", ".join(f"{repo} ({num})" for repo, num in hit.repos.most_common(4))
        lines.append(f"| `{name}` | {count} | {hit_confidence(hit)} | {hit.last_seen or '-'} | {repos or '-'} |")

    lines.extend(["", "## Top Evidence Files", ""])
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
    hits = summarize(args.skill_root, roots, args.max_file_bytes, args.days)
    write_markdown(hits, args.out_md)
    write_json(hits, args.out_json)
    active = sum(1 for hit in hits.values() if hit.count)
    print(f"skills_seen={active} report={args.out_md} json={args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
