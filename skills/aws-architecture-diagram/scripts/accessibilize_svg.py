#!/usr/bin/env python3
"""Add deterministic accessibility metadata without obscuring renderer provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from xml_safety import load_xml_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("raw_svg", type=Path)
    parser.add_argument("output_svg", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized(value: object) -> str:
    return " ".join(str(value or "").split())


def main() -> None:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    title = normalized(spec.get("title"))
    alt_text = normalized(spec.get("alt_text"))
    long_description = normalized(spec.get("long_description"))
    description = " ".join(part for part in (alt_text, long_description) if part)
    if not title or not alt_text:
        raise SystemExit("FAIL accessible SVG requires title and alt_text")

    raw_text = args.raw_svg.read_text(encoding="utf-8")
    match = re.search(r"<svg\b[^>]*>", raw_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise SystemExit("FAIL raw renderer output has no SVG root element")
    root_tag = match.group(0)
    if "aria-labelledby=" not in root_tag:
        root_tag = root_tag[:-1] + ' role="img" aria-labelledby="diagram-title diagram-description">'
    metadata = (
        f'<title id="diagram-title">{escape(title)}</title>'
        f'<desc id="diagram-description">{escape(description)}</desc>'
    )
    accessible_text = raw_text[: match.start()] + root_tag + metadata + raw_text[match.end() :]
    args.output_svg.parent.mkdir(parents=True, exist_ok=True)
    args.output_svg.write_text(accessible_text, encoding="utf-8")
    load_xml_root(args.output_svg)
    print(
        json.dumps(
            {
                "raw_svg": str(args.raw_svg),
                "accessible_svg": str(args.output_svg),
                "raw_sha256": sha256(args.raw_svg),
                "accessible_sha256": sha256(args.output_svg),
                "transformation": "insert-svg-title-desc-aria-v1",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
