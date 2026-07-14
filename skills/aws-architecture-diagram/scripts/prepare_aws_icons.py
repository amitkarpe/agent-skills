#!/usr/bin/env python3
"""Prepare a deterministic catalog from the official AWS Architecture Icons package."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

AWS_ICON_PAGE = "https://aws.amazon.com/architecture/icons/"
OFFICIAL_HOSTS = {"aws.amazon.com", "d1.awsstatic.com"}
ICON_EXTENSIONS = {".svg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-zip", type=Path, help="Local official AWS icon package ZIP")
    parser.add_argument("--source-page", default=AWS_ICON_PAGE)
    parser.add_argument("--package-url", help="Explicit official d1.awsstatic.com icon package URL")
    parser.add_argument(
        "--official-local-package",
        action="store_true",
        help="Assert that --package-zip was downloaded unchanged from the official AWS Architecture Icons page",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=45)
    return parser.parse_args()


def fetch_bytes(url: str, timeout: int) -> bytes:
    host = urllib.parse.urlparse(url).hostname
    if host not in OFFICIAL_HOSTS:
        raise ValueError(f"refusing non-official host: {host}")
    request = urllib.request.Request(url, headers={"User-Agent": "aws-architecture-diagram-skill/2"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def discover_package_url(source_page: str, timeout: int) -> str:
    content = fetch_bytes(source_page, timeout).decode("utf-8", errors="replace")
    content = html.unescape(content).replace("\\/", "/")
    candidates = re.findall(
        r"https://d1\.awsstatic\.com/[^\"'<>\s]+Icon-package_[^\"'<>\s]+\.zip",
        content,
        flags=re.IGNORECASE,
    )
    if not candidates:
        raise RuntimeError("could not discover the official AWS icon package URL")
    return sorted(set(candidates))[-1]


def safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            member_path = (destination / member.filename).resolve()
            if destination not in member_path.parents and member_path != destination:
                raise ValueError(f"unsafe ZIP member: {member.filename}")
        handle.extractall(destination)


def extract_nested_zips(root: Path, max_depth: int = 2) -> None:
    processed: set[Path] = set()
    for depth in range(max_depth):
        archives = [p for p in root.rglob("*.zip") if p not in processed]
        if not archives:
            break
        for archive in archives:
            processed.add(archive)
            target = archive.with_suffix("")
            target.mkdir(parents=True, exist_ok=True)
            try:
                safe_extract(archive, target)
            except zipfile.BadZipFile:
                continue


def normalize_key(value: str) -> str:
    value = value.replace("&", " and ")
    value = re.sub(r"(?i)^(arch|res|resource|architecture|category)[-_ ]+", "", value)
    value = re.sub(r"(?i)[-_ ]+(16|32|48|64|128|256)(px)?$", "", value)
    value = re.sub(r"(?i)[-_ ]+(light|dark)(-bg|_bg| background)?$", "", value)
    value = value.replace("™", "").replace("®", "")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value


def classify(path: Path) -> str:
    text = "/".join(path.parts).lower()
    stem = path.stem.lower()
    if "category" in text or stem.startswith("arch-category"):
        return "category"
    if "resource" in text or stem.startswith("res_") or stem.startswith("res-"):
        return "resource"
    return "service"


def icon_size(stem: str) -> int | None:
    match = re.search(r"(?:_|-)(16|32|48|64|128|256)(?:px)?$", stem, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def aliases_for(key: str) -> list[str]:
    aliases = {key}
    for prefix in ("amazon-", "aws-"):
        if key.startswith(prefix):
            aliases.add(key[len(prefix) :])
    replacements = {
        "amazon-simple-storage-service": "amazon-s3",
        "simple-storage-service": "s3",
        "amazon-elastic-compute-cloud": "amazon-ec2",
        "elastic-compute-cloud": "ec2",
        "aws-key-management-service": "aws-kms",
        "key-management-service": "kms",
    }
    if key in replacements:
        aliases.add(replacements[key])
    return sorted(aliases)


def score_icon(entry: dict) -> tuple[int, int, int, str]:
    kind_rank = {"service": 0, "resource": 20, "category": 40}[entry["kind"]]
    extension_rank = 0 if entry["extension"] == ".svg" else 5
    size = entry.get("size")
    size_rank = abs((size or 64) - 64)
    return kind_rank, extension_rank, size_rank, entry["original_path"]


def main() -> None:
    args = parse_args()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aws-icons-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        package_url = args.package_url
        package_path = temp_dir / "aws-icons.zip"

        local_package = bool(args.package_zip)
        if args.package_zip:
            source_zip = args.package_zip.expanduser().resolve()
            if not source_zip.is_file():
                raise SystemExit(f"package ZIP does not exist: {source_zip}")
            shutil.copy2(source_zip, package_path)
            package_url = package_url or f"file://{source_zip}"
        else:
            package_url = package_url or discover_package_url(args.source_page, args.timeout)
            package_path.write_bytes(fetch_bytes(package_url, args.timeout))

        if local_package:
            official = bool(args.official_local_package)
            verification = "user-asserted-official-local" if official else "unverified-local"
        else:
            official = urllib.parse.urlparse(package_url or "").hostname in OFFICIAL_HOSTS
            verification = "downloaded-from-official-host" if official else "unverified-remote"

        extracted = temp_dir / "extracted"
        extracted.mkdir()
        safe_extract(package_path, extracted)
        extract_nested_zips(extracted)

        icons = [p for p in extracted.rglob("*") if p.is_file() and p.suffix.lower() in ICON_EXTENSIONS]
        if not icons:
            raise SystemExit("no SVG or PNG icons found in package")

        staging = temp_dir / "staging"
        icon_dir = staging / "icons"
        icon_dir.mkdir(parents=True)
        entries: list[dict] = []
        used_names: set[str] = set()

        for source in sorted(icons):
            relative = source.relative_to(extracted)
            key = normalize_key(source.stem)
            if not key:
                continue
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", source.name)
            if safe_name in used_names:
                safe_name = f"{source.stem}-{digest[:10]}{source.suffix.lower()}"
            used_names.add(safe_name)
            destination = icon_dir / safe_name
            shutil.copy2(source, destination)
            entries.append(
                {
                    "key": key,
                    "aliases": aliases_for(key),
                    "kind": classify(relative),
                    "size": icon_size(source.stem),
                    "extension": source.suffix.lower(),
                    "path": f"icons/{safe_name}",
                    "original_path": relative.as_posix(),
                    "sha256": digest,
                }
            )

        lookup: dict[str, str] = {}
        all_aliases = sorted({alias for entry in entries for alias in entry["aliases"]})
        for alias in all_aliases:
            candidates = [entry for entry in entries if alias in entry["aliases"]]
            lookup[alias] = min(candidates, key=score_icon)["path"]

        release = Path(urllib.parse.urlparse(package_url or "").path).name or package_path.name
        catalog = {
            "schema_version": 1,
            "official": official,
            "verification": verification,
            "source_page": args.source_page,
            "package_url": package_url,
            "release": release,
            "prepared_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "package_sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
            "icon_count": len(entries),
            "lookup": lookup,
            "icons": entries,
        }
        (staging / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(staging, output)

    if not official:
        print("WARN icon package is catalogued as unverified; official icon validation will reject it")
    print(f"PASS output={output} icons={len(entries)} release={release} official={str(official).lower()} verification={verification}")


if __name__ == "__main__":
    main()
