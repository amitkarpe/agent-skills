#!/usr/bin/env python3
"""Preview or apply a curated skill exposure profile."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def read_profile(path: Path) -> list[str]:
    if not path.is_file():
        raise SystemExit(f"profile not found: {path}")
    names: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in seen:
            raise SystemExit(f"duplicate skill in profile {path}: {line}")
        seen.add(line)
        names.append(line)
    return names


def source_skill_dirs(skills_root: Path) -> dict[str, Path]:
    if not skills_root.is_dir():
        raise SystemExit(f"skills root not found: {skills_root}")
    result: dict[str, Path] = {}
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        if (skill_dir / "SKILL.md").is_file():
            result[skill_dir.name] = skill_dir.resolve()
    return result


def is_source_owned_symlink(path: Path, source_dirs: dict[str, Path]) -> bool:
    if not path.is_symlink():
        return False
    try:
        target = path.resolve(strict=False)
    except OSError:
        return False
    return target in source_dirs.values()


def active_source_owned(dest_root: Path, source_dirs: dict[str, Path]) -> set[str]:
    active: set[str] = set()
    if not dest_root.is_dir():
        return active
    for path in dest_root.iterdir():
        if is_source_owned_symlink(path, source_dirs):
            active.add(path.name)
    return active


def write_action_record(actions: dict[str, list[str]], record_dir: Path) -> Path:
    record_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = record_dir / f"skill-profile-apply-{stamp}.json"
    path.write_text(json.dumps(actions, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def print_actions(mode: str, dest_root: Path, source_dirs: dict[str, Path], to_link: list[str], to_unlink: list[str], unchanged: list[str]) -> None:
    print(f"mode={mode}")
    print(f"dest_root={dest_root}")
    print(f"link={len(to_link)} unlink={len(to_unlink)} unchanged={len(unchanged)}")
    for name in to_link:
        print(f"LINK   {name} -> {source_dirs[name]}")
    for name in to_unlink:
        print(f"UNLINK {name} from {dest_root / name}")
    for name in unchanged:
        print(f"KEEP   {name}")


def apply_actions(dest_root: Path, source_dirs: dict[str, Path], to_link: list[str], to_unlink: list[str]) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    for name in to_unlink:
        path = dest_root / name
        if not is_source_owned_symlink(path, source_dirs):
            raise SystemExit(f"refusing to unlink non-source-owned path: {path}")
        path.unlink()
    for name in to_link:
        path = dest_root / name
        if path.exists() or path.is_symlink():
            raise SystemExit(f"refusing to overwrite existing destination: {path}")
        os.symlink(source_dirs[name], path)


def restore_from_record(record_path: Path, dest_root: Path, source_dirs: dict[str, Path], apply: bool) -> int:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    to_link = [name for name in record.get("unlinked", []) if name in source_dirs]
    to_unlink = [name for name in record.get("linked", []) if name in source_dirs]
    print(f"restore_record={record_path}")
    print_actions("restore-apply" if apply else "restore-dry-run", dest_root, source_dirs, to_link, to_unlink, [])
    if not apply:
        print("dry-run only; no files changed")
        return 0
    apply_actions(dest_root, source_dirs, to_link, to_unlink)
    print("restore complete")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="append", help="Profile name from profiles/<name>.txt or an explicit path. Repeat to combine profiles.")
    parser.add_argument("--restore-record", help="Reverse a prior --apply action record")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--dest-root", default=str(Path.home() / ".codex" / "skills"))
    parser.add_argument("--apply", action="store_true", help="Mutate ~/.codex/skills. Default is dry-run.")
    parser.add_argument("--record-dir", default=str(Path.home() / ".AGENTS-temp" / "agent-skills" / "profile-apply"))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    skills_root = repo_root / "skills"
    profiles_root = repo_root / "profiles"
    dest_root = Path(args.dest_root).expanduser()
    source_dirs = source_skill_dirs(skills_root)

    if args.restore_record:
        return restore_from_record(Path(args.restore_record).expanduser(), dest_root, source_dirs, args.apply)
    if not args.profile:
        raise SystemExit("provide --profile or --restore-record")

    profile_paths: list[Path] = []
    desired_order: list[str] = []
    seen_desired: set[str] = set()
    for item in args.profile:
        profile_path = Path(item).expanduser()
        if not profile_path.exists():
            profile_path = profiles_root / f"{item}.txt"
        profile_paths.append(profile_path)
        for name in read_profile(profile_path):
            if name not in seen_desired:
                desired_order.append(name)
                seen_desired.add(name)
    desired = set(desired_order)
    unknown = sorted(desired - set(source_dirs))
    if unknown:
        raise SystemExit(f"profile contains unknown skills: {', '.join(unknown)}")

    active = active_source_owned(dest_root, source_dirs)
    to_link = [name for name in desired_order if name not in active]
    to_unlink = sorted(active - desired)
    unchanged = [name for name in desired_order if name in active]

    profile_name = "+".join(path.stem for path in profile_paths)
    print(f"profile={profile_name}")
    print(f"desired={len(desired)} active_source_owned={len(active)} link={len(to_link)} unlink={len(to_unlink)} unchanged={len(unchanged)}")
    print_actions("apply" if args.apply else "dry-run", dest_root, source_dirs, to_link, to_unlink, unchanged)

    if not args.apply:
        print("dry-run only; no files changed")
        return 0

    actions = {
        "profile": profile_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dest_root": str(dest_root),
        "linked": [],
        "unlinked": [],
        "kept": unchanged,
    }
    apply_actions(dest_root, source_dirs, to_link, to_unlink)
    actions["unlinked"] = to_unlink
    actions["linked"] = to_link
    record = write_action_record(actions, Path(args.record_dir).expanduser())
    print(f"action_record={record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
