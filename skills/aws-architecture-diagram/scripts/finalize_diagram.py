#!/usr/bin/env python3
"""Finalize the latest reviewed diagram after a mandatory two-pass build."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--name", default="architecture")
    parser.add_argument("--accept-preview", action="store_true")
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def require(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"FAIL required artefact is missing or empty: {path}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    if not output_dir.is_dir():
        raise SystemExit(f"FAIL output directory does not exist: {output_dir}")

    pass1_manifest_path = require(output_dir / f"{args.name}.pass-01.manifest.json")
    pass2_manifest_path = require(output_dir / f"{args.name}.pass-02.manifest.json")
    pass1 = read_json(pass1_manifest_path)
    pass2 = read_json(pass2_manifest_path)

    if int(pass1.get("pass_number", 0)) != 1 or int(pass2.get("pass_number", 0)) != 2:
        raise SystemExit("FAIL finalization requires review pass 1 and pass 2")
    if not str(pass2.get("changes", "")).strip():
        raise SystemExit("FAIL pass 2 does not record visual corrections")
    if pass2.get("quality_gate") != "PASS":
        raise SystemExit(f"FAIL pass 2 quality gate is {pass2.get('quality_gate')}")
    if pass2.get("status") == "WARN" and not args.allow_warnings:
        # Native AWS fallback warnings are expected in offline environments; require explicit acceptance.
        raise SystemExit("FAIL pass 2 contains warnings; re-run with --allow-warnings only after reviewing them")
    if pass2.get("renderer") != "drawio-cli" and not args.accept_preview:
        raise SystemExit(
            "FAIL pass 2 used the preview renderer; exact draw.io export is required unless --accept-preview is explicit"
        )

    artefacts = pass2.get("artefacts", {})
    required_keys = ("spec", "drawio", "svg", "raw_svg", "png", "review_json", "review_markdown")
    source_paths = {key: require(output_dir / str(artefacts.get(key, ""))) for key in required_keys}
    provenance = pass2.get("renderer_provenance", {})
    expected_hashes = {
        "raw_svg": provenance.get("raw_svg_sha256"),
        "svg": provenance.get("accessible_svg_sha256"),
    }
    for key, expected in expected_hashes.items():
        actual = sha256(source_paths[key])
        if not expected or actual != expected:
            raise SystemExit(
                f"FAIL pass 2 {key} provenance hash mismatch: expected={expected!r} actual={actual}"
            )

    final_paths = {
        "spec": output_dir / f"{args.name}.spec.json",
        "drawio": output_dir / f"{args.name}.drawio",
        "svg": output_dir / f"{args.name}.svg",
        "raw_svg": output_dir / f"{args.name}.renderer-raw.svg",
        "png": output_dir / f"{args.name}.png",
        "review_json": output_dir / f"{args.name}.review.json",
        "review_markdown": output_dir / f"{args.name}.review-summary.md",
    }
    for key, source in source_paths.items():
        shutil.copy2(source, final_paths[key])

    pass1_review = read_json(require(output_dir / f"{args.name}.pass-01.review.json"))
    pass2_review = read_json(source_paths["review_json"])
    summary_lines = [
        f"# Final Diagram Review — {args.name}",
        "",
        "## Result",
        "",
        f"- **Final quality gate:** {pass2_review.get('quality_gate')}",
        f"- **Final status:** {pass2_review.get('status')}",
        f"- **Final renderer:** {pass2_review.get('renderer')} ({pass2_review.get('renderer_confidence')})",
        f"- **Pass 2 changes:** {pass2.get('changes')}",
        "",
        "## Review history",
        "",
        f"- Pass 1: {pass1_review.get('status')} — {len(pass1_review.get('errors', []))} errors, {len(pass1_review.get('warnings', []))} warnings",
        f"- Pass 2: {pass2_review.get('status')} — {len(pass2_review.get('errors', []))} errors, {len(pass2_review.get('warnings', []))} warnings",
        "",
        "## Final artefacts",
        "",
        f"- `{final_paths['drawio'].name}` — editable source",
        f"- `{final_paths['svg'].name}` — scalable preview",
        f"- `{final_paths['raw_svg'].name}` — unmodified renderer SVG for provenance",
        f"- `{final_paths['png'].name}` — raster preview",
        f"- `{final_paths['spec'].name}` — canonical architecture specification",
        f"- `{final_paths['review_json'].name}` — machine-readable QA result",
    ]
    if pass2_review.get("renderer") != "drawio-cli":
        summary_lines.extend(
            [
                "",
                "## Renderer limitation",
                "",
                "The final preview was produced by the skill's subset renderer, not draw.io Desktop. "
                "Open the `.drawio` file and export once with draw.io Desktop before production or executive use.",
            ]
        )
    final_paths["review_markdown"].write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    final_manifest = {
        "schema_version": 1,
        "name": args.name,
        "finalized_from_pass": 2,
        "renderer": pass2_review.get("renderer"),
        "renderer_confidence": pass2_review.get("renderer_confidence"),
        "quality_gate": pass2_review.get("quality_gate"),
        "status": pass2_review.get("status"),
        "changes": pass2.get("changes"),
        "accessibility": pass2_review.get("accessibility", {}),
        "renderer_provenance": pass2.get("renderer_provenance", {}),
        "artefacts": {key: path.name for key, path in final_paths.items()},
        "artefact_sha256": {key: sha256(path) for key, path in final_paths.items()},
    }
    manifest_path = output_dir / f"{args.name}.manifest.json"
    manifest_path.write_text(json.dumps(final_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"PASS finalized name={args.name} renderer={final_manifest['renderer']} "
        f"drawio={final_paths['drawio']} png={final_paths['png']} manifest={manifest_path}"
    )


if __name__ == "__main__":
    main()
