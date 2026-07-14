#!/usr/bin/env python3
"""Build one diagram review pass from a canonical JSON specification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--name", default="architecture")
    parser.add_argument("--pass-number", type=int, required=True)
    parser.add_argument("--changes", default="")
    parser.add_argument("--renderer", choices=("auto", "drawio", "preview"), default="auto")
    parser.add_argument("--official-icons", type=Path, default=root / "assets/aws-official/current")
    parser.add_argument("--fallback-icons", type=Path, default=root / "assets/fallback-icons")
    parser.add_argument("--native-map", type=Path, default=root / "assets/native-aws4-map.json")
    parser.add_argument("--allow-bundled-fallback", action="store_true")
    parser.add_argument("--allow-unverified-aws-icons", action="store_true")
    parser.add_argument("--require-official-aws-icons", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--preview-scale", type=float, default=1.0)
    return parser.parse_args()


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command), flush=True)
    completed = subprocess.run(command, check=False, text=True, capture_output=True, env=env)
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="" if completed.stderr.endswith("\n") else "\n")
    return completed


def validate_name(name: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if not name or any(character not in allowed for character in name):
        raise SystemExit("FAIL --name may contain only letters, digits, hyphen, and underscore")
    return name


def exact_renderer_available() -> bool:
    drawio_bin = os.environ.get("DRAWIO_BIN")
    if drawio_bin and Path(drawio_bin).exists():
        return True
    return any(shutil.which(candidate) for candidate in ("drawio", "draw.io", "draw.io.exe"))


def read_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"review report must be a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.pass_number < 1:
        raise SystemExit("FAIL pass number must be >= 1")
    if args.pass_number >= 2 and not args.changes.strip():
        raise SystemExit("FAIL pass 2 and later require --changes")

    name = validate_name(args.name)
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    spec = args.spec.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not spec.is_file():
        raise SystemExit(f"FAIL specification does not exist: {spec}")

    stem = f"{name}.pass-{args.pass_number:02d}"
    drawio = output_dir / f"{stem}.drawio"
    svg = output_dir / f"{stem}.svg"
    png = output_dir / f"{stem}.png"
    review_json = output_dir / f"{stem}.review.json"
    review_md = output_dir / f"{stem}.review.md"
    manifest = output_dir / f"{stem}.manifest.json"
    spec_snapshot = output_dir / f"{stem}.spec.json"
    raw_svg = output_dir / f"{stem}.renderer-raw.svg"

    validate_spec_command = [sys.executable, str(scripts / "validate_spec.py"), str(spec)]
    if args.strict:
        validate_spec_command.append("--strict")
    completed = run(validate_spec_command)
    if completed.returncode:
        raise SystemExit(completed.returncode)

    generate_command = [
        sys.executable,
        str(scripts / "generate_drawio.py"),
        str(spec),
        str(drawio),
        "--official-icons",
        str(args.official_icons),
        "--fallback-icons",
        str(args.fallback_icons),
        "--native-map",
        str(args.native_map),
    ]
    if args.allow_bundled_fallback:
        generate_command.append("--allow-bundled-fallback")
    completed = run(generate_command)
    if completed.returncode:
        raise SystemExit(completed.returncode)

    validate_drawio_command = [sys.executable, str(scripts / "validate_drawio.py"), str(drawio)]
    if args.require_official_aws_icons:
        validate_drawio_command.append("--require-official-aws-icons")
    if args.allow_unverified_aws_icons:
        validate_drawio_command.append("--allow-unverified-aws-icons")
    if args.strict:
        validate_drawio_command.append("--strict")
    completed = run(validate_drawio_command)
    if completed.returncode:
        raise SystemExit(completed.returncode)

    use_exact = args.renderer == "drawio" or (args.renderer == "auto" and exact_renderer_available())
    if args.renderer == "drawio" and not exact_renderer_available():
        raise SystemExit("FAIL exact draw.io renderer requested but draw.io Desktop CLI was not found")

    renderer_label: str
    if use_exact:
        renderer_label = "drawio-cli"
        completed = run([str(scripts / "export_drawio.sh"), str(drawio), str(output_dir)])
        if completed.returncode:
            if args.renderer == "drawio":
                raise SystemExit(completed.returncode)
            print("WARN exact draw.io export failed; using preview renderer", file=sys.stderr)
            renderer_label = "preview-renderer"
            completed = run(
                [
                    sys.executable,
                    str(scripts / "render_preview.py"),
                    str(drawio),
                    str(svg),
                    str(png),
                    "--scale",
                    str(args.preview_scale),
                ]
            )
            if completed.returncode:
                raise SystemExit(completed.returncode)
    else:
        renderer_label = "preview-renderer"
        completed = run(
            [
                sys.executable,
                str(scripts / "render_preview.py"),
                str(drawio),
                str(svg),
                str(png),
                "--scale",
                str(args.preview_scale),
            ]
        )
        if completed.returncode:
            raise SystemExit(completed.returncode)

    shutil.copy2(svg, raw_svg)
    completed = run(
        [
            sys.executable,
            str(scripts / "accessibilize_svg.py"),
            str(spec),
            str(raw_svg),
            str(svg),
        ]
    )
    if completed.returncode:
        raise SystemExit(completed.returncode)

    review_command = [
        sys.executable,
        str(scripts / "review_render.py"),
        str(drawio),
        str(svg),
        str(png),
        "--raw-svg",
        str(raw_svg),
        "--renderer",
        renderer_label,
        "--pass-number",
        str(args.pass_number),
        "--changes",
        args.changes,
        "--output-json",
        str(review_json),
        "--output-md",
        str(review_md),
    ]
    if args.require_official_aws_icons:
        review_command.append("--require-official-aws-icons")
    if args.allow_unverified_aws_icons:
        review_command.append("--allow-unverified-aws-icons")
    if args.strict:
        review_command.append("--strict")
    completed = run(review_command)
    if completed.returncode:
        raise SystemExit(completed.returncode)

    shutil.copy2(spec, spec_snapshot)
    report = read_report(review_json)
    manifest_data = {
        "schema_version": 1,
        "name": name,
        "pass_number": args.pass_number,
        "changes": args.changes.strip(),
        "renderer": renderer_label,
        "quality_gate": report.get("quality_gate"),
        "status": report.get("status"),
        "source_spec": str(spec),
        "accessibility": report.get("accessibility", {}),
        "renderer_provenance": {
            "raw_svg_sha256": sha256(raw_svg),
            "accessible_svg_sha256": sha256(svg),
            "accessible_transformation": "insert-svg-title-desc-aria-v1",
        },
        "artefacts": {
            "spec": spec_snapshot.name,
            "drawio": drawio.name,
            "svg": svg.name,
            "raw_svg": raw_svg.name,
            "png": png.name,
            "review_json": review_json.name,
            "review_markdown": review_md.name,
        },
    }
    manifest.write_text(json.dumps(manifest_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"PASS build-review pass={args.pass_number} renderer={renderer_label} "
        f"drawio={drawio} svg={svg} png={png} review={review_md}"
    )


if __name__ == "__main__":
    main()
