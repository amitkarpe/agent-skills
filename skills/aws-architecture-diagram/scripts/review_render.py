#!/usr/bin/env python3
"""Create a deterministic visual-quality report for a rendered draw.io diagram.

The report combines XML geometry checks, the draw.io validator, SVG metadata, and
PNG canvas/margin checks. It does not pretend to replace human visual judgment;
it produces a repeatable gate and a concise review checklist for the final pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET
from PIL import Image, ImageChops, ImageStat
from xml_safety import load_xml_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("drawio", type=Path)
    parser.add_argument("svg", type=Path)
    parser.add_argument("png", type=Path)
    parser.add_argument("--raw-svg", type=Path)
    parser.add_argument("--renderer", choices=("drawio-cli", "preview-renderer"), required=True)
    parser.add_argument("--pass-number", type=int, required=True)
    parser.add_argument("--changes", default="")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--require-official-aws-icons", action="store_true")
    parser.add_argument("--allow-unverified-aws-icons", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def style_value(style: str, key: str) -> str | None:
    match = re.search(rf"(?:^|;){re.escape(key)}=([^;]*)(?:;|$)", style)
    return match.group(1) if match else None


def style_float(style: str, key: str, default: float) -> float:
    value = style_value(style, key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def geometry(cell: ET.Element) -> tuple[float, float, float, float] | None:
    geom = cell.find("mxGeometry")
    if geom is None:
        return None
    try:
        return tuple(float(geom.get(key, "0")) for key in ("x", "y", "width", "height"))
    except ValueError:
        return None


def run_validator(args: argparse.Namespace) -> tuple[int, list[str], list[str], str]:
    validator = Path(__file__).with_name("validate_drawio.py")
    command = [sys.executable, str(validator), str(args.drawio)]
    if args.require_official_aws_icons:
        command.append("--require-official-aws-icons")
    if args.allow_unverified_aws_icons:
        command.append("--allow-unverified-aws-icons")
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    warnings = [line[5:].strip() for line in combined.splitlines() if line.startswith("WARN ")]
    failures = [line[5:].strip() for line in combined.splitlines() if line.startswith("FAIL ")]
    if completed.returncode and not failures:
        failures.append(f"draw.io validator exited with status {completed.returncode}")
    return completed.returncode, warnings, failures, combined


def parse_length(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"\s*([0-9.]+)", value)
    return float(match.group(1)) if match else None


def png_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        corner_samples = [
            image.getpixel((0, 0)),
            image.getpixel((max(0, width - 1), 0)),
            image.getpixel((0, max(0, height - 1))),
            image.getpixel((max(0, width - 1), max(0, height - 1))),
        ]
        background = tuple(round(sum(sample[channel] for sample in corner_samples) / 4) for channel in range(3))
        background_image = Image.new("RGB", image.size, background)
        difference = ImageChops.difference(image, background_image).convert("L")
        # Ignore anti-aliasing noise and nearly-white pixels.
        mask = difference.point(lambda value: 255 if value > 10 else 0)
        bbox = mask.getbbox()
        if bbox:
            left, top, right, bottom = bbox
            margins = {
                "left": left,
                "top": top,
                "right": width - right,
                "bottom": height - bottom,
            }
            content_width = max(0, right - left)
            content_height = max(0, bottom - top)
            occupancy = (content_width * content_height) / max(1, width * height)
        else:
            margins = {"left": width, "top": height, "right": width, "bottom": height}
            occupancy = 0.0
        stat = ImageStat.Stat(image)
        mean_rgb = [round(value, 2) for value in stat.mean]
        return {
            "width": width,
            "height": height,
            "background_rgb": list(background),
            "content_bbox": list(bbox) if bbox else None,
            "margins_px": margins,
            "occupancy_ratio": round(occupancy, 4),
            "mean_rgb": mean_rgb,
        }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def xml_metrics(path: Path) -> dict[str, Any]:
    root = load_xml_root(path)
    diagram = root.find("diagram")
    model = root.find(".//mxGraphModel")
    if model is None:
        raise ValueError("mxGraphModel is missing")
    cells = root.findall(".//mxCell")
    kinds = Counter(cell.get("data-kind", "untyped") for cell in cells)
    page_width = float(model.get("pageWidth", "0"))
    page_height = float(model.get("pageHeight", "0"))
    fonts: list[float] = []
    transparent_text = 0
    text_count = 0
    for cell in cells:
        if cell.get("vertex") != "1" or not (cell.get("value") or "").strip():
            continue
        style = cell.get("style") or ""
        text_count += 1
        fonts.append(style_float(style, "fontSize", 0))
        if style_value(style, "fillColor") == "none" and style_value(style, "strokeColor") == "none":
            transparent_text += 1
    icon_sources = Counter(
        cell.get("data-icon-source", "unknown")
        for cell in cells
        if cell.get("data-kind") == "resource-icon"
    )
    edge_colors = Counter(
        cell.get("data-resolved-color", "unknown")
        for cell in cells
        if cell.get("data-kind") == "relationship"
    )
    edge_styles = Counter(
        "dashed" if cell.get("data-dashed") == "1" else "solid"
        for cell in cells
        if cell.get("data-kind") == "relationship"
    )
    resource_geometries = {
        cell.get("data-resource-id", ""): geometry(cell)
        for cell in cells
        if cell.get("data-kind") == "resource-card"
    }
    return {
        "page_width": page_width,
        "page_height": page_height,
        "cell_count": len(cells),
        "kind_counts": dict(sorted(kinds.items())),
        "resource_count": kinds.get("resource-card", 0),
        "edge_count": kinds.get("relationship", 0),
        "caption_count": kinds.get("relationship-caption", 0),
        "legend_present": kinds.get("legend-shell", 0) > 0,
        "text_count": text_count,
        "transparent_text_count": transparent_text,
        "minimum_font_size": min(fonts) if fonts else None,
        "icon_sources": dict(sorted(icon_sources.items())),
        "edge_colors": dict(sorted(edge_colors.items())),
        "edge_styles": dict(sorted(edge_styles.items())),
        "resource_geometries": {key: list(value) if value else None for key, value in resource_geometries.items()},
        "alt_text": (diagram.get("data-alt-text", "") if diagram is not None else ""),
        "long_description": (diagram.get("data-long-description", "") if diagram is not None else ""),
    }


def svg_metrics(path: Path) -> dict[str, Any]:
    root = load_xml_root(path)
    width = parse_length(root.get("width"))
    height = parse_length(root.get("height"))
    view_box = root.get("viewBox")
    direct_children = list(root)
    title = next((child.text or "" for child in direct_children if child.tag.rsplit("}", 1)[-1] == "title"), "")
    description = next((child.text or "" for child in direct_children if child.tag.rsplit("}", 1)[-1] == "desc"), "")
    return {
        "width": width,
        "height": height,
        "viewBox": view_box,
        "bytes": path.stat().st_size,
        "title": title,
        "description": description,
        "role": root.get("role"),
        "aria_labelledby": root.get("aria-labelledby"),
        "sha256": sha256(path),
    }


def make_report(args: argparse.Namespace) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    for label, path in (("drawio", args.drawio), ("svg", args.svg), ("png", args.png)):
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty {label} artefact: {path}")

    xml: dict[str, Any] = {}
    svg: dict[str, Any] = {}
    png: dict[str, Any] = {}
    validator_output = ""
    if args.drawio.is_file():
        try:
            xml = xml_metrics(args.drawio)
        except Exception as exc:  # noqa: BLE001 - report all parse failures in the review
            errors.append(f"unable to analyse draw.io XML: {exc}")
        _, validator_warnings, validator_failures, validator_output = run_validator(args)
        warnings.extend(validator_warnings)
        errors.extend(validator_failures)
    if args.svg.is_file():
        try:
            svg = svg_metrics(args.svg)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"unable to analyse SVG: {exc}")
    raw_svg: dict[str, Any] = {}
    if args.raw_svg:
        if not args.raw_svg.is_file() or args.raw_svg.stat().st_size == 0:
            errors.append(f"missing or empty raw SVG provenance artefact: {args.raw_svg}")
        else:
            raw_svg = {"path": str(args.raw_svg.resolve()), "sha256": sha256(args.raw_svg)}
    if args.png.is_file():
        try:
            png = png_metrics(args.png)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"unable to analyse PNG: {exc}")

    if png and (svg or xml):
        # Exact draw.io exports are cropped to rendered bounds, so their ratio
        # should match the companion SVG rather than the configured page size.
        # The preview renderer preserves the configured page dimensions.
        if args.renderer == "drawio-cli" and svg.get("width") and svg.get("height"):
            expected_width = float(svg["width"])
            expected_height = float(svg["height"])
            expected_label = "SVG"
        else:
            expected_width = float(xml.get("page_width", 0))
            expected_height = float(xml.get("page_height", 0))
            expected_label = "page"
        expected_ratio = expected_width / max(1.0, expected_height)
        actual_ratio = png["width"] / max(1.0, png["height"])
        if abs(expected_ratio - actual_ratio) > 0.01:
            errors.append(
                f"PNG aspect ratio {actual_ratio:.4f} does not match {expected_label} ratio {expected_ratio:.4f}"
            )
        scale_x = png["width"] / max(1.0, expected_width)
        scale_y = png["height"] / max(1.0, expected_height)
        if abs(scale_x - scale_y) > 0.02:
            errors.append(f"PNG uses non-uniform scale: x={scale_x:.3f}, y={scale_y:.3f}")

    if xml:
        if xml.get("text_count") != xml.get("transparent_text_count"):
            errors.append(
                f"not all visible text cells are transparent: {xml.get('transparent_text_count')}/{xml.get('text_count')}"
            )
        minimum_font = xml.get("minimum_font_size")
        if minimum_font is not None and minimum_font < 11:
            warnings.append(f"minimum font size is {minimum_font:g}px; avoid shrinking labels")
        if xml.get("edge_count", 0) > 0 and not xml.get("legend_present"):
            unique_edge_conventions = len(xml.get("edge_colors", {})) + len(xml.get("edge_styles", {}))
            if unique_edge_conventions > 3:
                warnings.append("several connector conventions are present but the diagram has no legend")
        if xml.get("resource_count", 0) > 20:
            warnings.append("resource density is high; consider overview and detail pages")
        alt_text = str(xml.get("alt_text", ""))
        long_description = str(xml.get("long_description", ""))
        expected_description = " ".join(part for part in (alt_text, long_description) if part)
        if not alt_text:
            errors.append("draw.io metadata has no alt_text")
        if svg:
            if not svg.get("title"):
                errors.append("accessible SVG has no title")
            if svg.get("description") != expected_description:
                errors.append("accessible SVG description does not match draw.io accessibility metadata")
            if svg.get("role") != "img" or svg.get("aria_labelledby") != "diagram-title diagram-description":
                errors.append("accessible SVG role/aria-labelledby metadata is missing or inconsistent")

    if png:
        occupancy = float(png.get("occupancy_ratio", 0))
        if occupancy < 0.18:
            warnings.append(f"canvas occupancy is only {occupancy:.1%}; diagram may feel too sparse")
        elif occupancy > 0.94:
            warnings.append(f"canvas occupancy is {occupancy:.1%}; diagram may feel crowded")
        margins = png.get("margins_px", {})
        min_margin = min(margins.values()) if margins else 0
        if min_margin < 8:
            warnings.append(f"rendered content approaches a page edge; minimum margin is {min_margin}px")

    if args.renderer == "preview-renderer":
        recommendations.append(
            "Open the .drawio in draw.io Desktop and run an exact export before production or executive use."
        )
    if args.pass_number >= 2 and not args.changes.strip():
        errors.append("pass 2 must record the visual corrections applied after pass 1")

    # Keep issue order stable and remove duplicates.
    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    recommendations = list(dict.fromkeys(recommendations))
    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    quality_gate = "PASS" if not errors else "FAIL"
    if args.strict and warnings:
        status = "FAIL"
        quality_gate = "FAIL"
        errors.append("strict mode treats warnings as failures")

    return {
        "schema_version": 1,
        "pass_number": args.pass_number,
        "changes": args.changes.strip(),
        "renderer": args.renderer,
        "renderer_confidence": "exact" if args.renderer == "drawio-cli" else "layout-preview",
        "status": status,
        "quality_gate": quality_gate,
        "errors": errors,
        "warnings": warnings,
        "recommendations": recommendations,
        "artefacts": {
            "drawio": str(args.drawio.resolve()),
            "svg": str(args.svg.resolve()),
            "png": str(args.png.resolve()),
            "raw_svg": str(args.raw_svg.resolve()) if args.raw_svg else None,
        },
        "accessibility": {
            "alt_text": xml.get("alt_text", ""),
            "long_description": xml.get("long_description", ""),
            "svg_title": svg.get("title", ""),
            "svg_description": svg.get("description", ""),
            "raw_svg_sha256": raw_svg.get("sha256"),
            "accessible_svg_sha256": svg.get("sha256"),
            "transformation": "insert-svg-title-desc-aria-v1",
        },
        "metrics": {"xml": xml, "svg": svg, "png": png},
        "validator_output": validator_output,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Diagram Review — Pass {report['pass_number']}",
        "",
        f"- **Status:** {report['status']}",
        f"- **Quality gate:** {report['quality_gate']}",
        f"- **Renderer:** {report['renderer']} ({report['renderer_confidence']})",
        f"- **Alt text:** {report.get('accessibility', {}).get('alt_text', 'missing')}",
        f"- **Raw SVG SHA-256:** {report.get('accessibility', {}).get('raw_svg_sha256', 'n/a')}",
        f"- **Accessible SVG SHA-256:** {report.get('accessibility', {}).get('accessible_svg_sha256', 'n/a')}",
    ]
    if report.get("changes"):
        lines.append(f"- **Changes after previous pass:** {report['changes']}")
    lines.extend(["", "## Critical findings"])
    if report["errors"]:
        lines.extend(f"- ❌ {item}" for item in report["errors"])
    else:
        lines.append("- ✅ No deterministic blocking defects detected.")
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- ⚠️ {item}" for item in report["warnings"])
    else:
        lines.append("- ✅ No deterministic warnings.")
    lines.extend(["", "## End-user review checklist"])
    lines.extend(
        [
            "- [ ] Read every title, service label, subnet label, and connector caption at normal zoom.",
            "- [ ] Confirm no text, icon, arrow, or legend item overlaps another object.",
            "- [ ] Confirm primary request flow is visually dominant and arrow direction is unambiguous.",
            "- [ ] Confirm border, fill, and connector colours carry consistent meanings.",
            "- [ ] Confirm official/icon provenance is appropriate for the deliverable.",
            "- [ ] Confirm whitespace and visual balance are suitable for the intended audience.",
        ]
    )
    if report["recommendations"]:
        lines.extend(["", "## Recommendations"])
        lines.extend(f"- {item}" for item in report["recommendations"])
    metrics = report.get("metrics", {})
    xml = metrics.get("xml", {})
    png = metrics.get("png", {})
    lines.extend(
        [
            "",
            "## Metrics",
            f"- Resources: {xml.get('resource_count', 'n/a')}",
            f"- Relationships: {xml.get('edge_count', 'n/a')}",
            f"- Text transparency: {xml.get('transparent_text_count', 'n/a')}/{xml.get('text_count', 'n/a')}",
            f"- PNG: {png.get('width', 'n/a')} × {png.get('height', 'n/a')}",
            f"- Canvas occupancy: {png.get('occupancy_ratio', 'n/a')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    report = make_report(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(report), encoding="utf-8")
    print(
        f"{report['status']} review pass={args.pass_number} renderer={args.renderer} "
        f"errors={len(report['errors'])} warnings={len(report['warnings'])} "
        f"json={args.output_json} markdown={args.output_md}"
    )
    if report["quality_gate"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
