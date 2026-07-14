#!/usr/bin/env python3
"""Validate draw.io structure, portability, provenance, readability, and geometry."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Iterable

import defusedxml.ElementTree as ET
from clearance_lint import lint_clearance
from xml_safety import XmlSafetyError, load_xml_root, safe_text

TRANSPARENT_TEXT_KINDS = {
    "resource-label",
    "relationship-caption",
    "boundary-label",
    "group-label",
    "title",
    "subtitle",
    "legend-title",
    "legend-label",
    "footer",
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("drawio", type=Path)
    parser.add_argument("--aws4-catalog", type=Path, default=root / "assets/aws4-shapes.json")
    parser.add_argument("--require-official-aws-icons", action="store_true")
    parser.add_argument("--allow-unverified-aws-icons", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    return parser.parse_args()


def load_aws4_catalog(path: Path) -> tuple[set[str], str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        categories = data["categories"]
        shapes = {
            str(shape)
            for category in categories.values()
            for shape in category.get("shapes", [])
        }
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FAIL invalid AWS4 shape catalog: {safe_text(exc)}") from exc
    if not shapes:
        raise SystemExit("FAIL AWS4 shape catalog is empty")
    return shapes, str(data.get("version", "unknown"))


def geometry(cell: ET.Element) -> tuple[float, float, float, float] | None:
    item = cell.find("mxGeometry")
    if item is None:
        return None
    try:
        return tuple(float(item.get(key, "0")) for key in ("x", "y", "width", "height"))
    except ValueError:
        return None


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


def overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float], padding: float = 0) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax - padding < bx + bw + padding
        and ax + aw + padding > bx - padding
        and ay - padding < by + bh + padding
        and ay + ah + padding > by - padding
    )


def point_on_rect(rect: tuple[float, float, float, float], rx: float, ry: float) -> tuple[float, float]:
    x, y, width, height = rect
    return x + width * rx, y + height * ry


def automatic_anchor(source: tuple[float, float, float, float], target: tuple[float, float, float, float], source_side: bool) -> tuple[float, float]:
    sx, sy, sw, sh = source
    tx, ty, tw, th = target
    scx, scy = sx + sw / 2, sy + sh / 2
    tcx, tcy = tx + tw / 2, ty + th / 2
    dx, dy = tcx - scx, tcy - scy
    if abs(dx) >= abs(dy):
        if source_side:
            return (sx + sw, scy) if dx >= 0 else (sx, scy)
        return (tx, tcy) if dx >= 0 else (tx + tw, tcy)
    if source_side:
        return (scx, sy + sh) if dy >= 0 else (scx, sy)
    return (tcx, ty) if dy >= 0 else (tcx, ty + th)


def edge_points(edge: ET.Element, cards: dict[str, tuple[float, float, float, float]]) -> list[tuple[float, float]]:
    source_id = edge.get("source")
    target_id = edge.get("target")
    if source_id not in cards or target_id not in cards:
        return []
    style = edge.get("style") or ""
    source_rect = cards[source_id]
    target_rect = cards[target_id]
    exit_x = style_float(style, "exitX", math.nan)
    exit_y = style_float(style, "exitY", math.nan)
    entry_x = style_float(style, "entryX", math.nan)
    entry_y = style_float(style, "entryY", math.nan)
    if math.isnan(exit_x) or math.isnan(exit_y):
        source_point = automatic_anchor(source_rect, target_rect, True)
    else:
        source_point = point_on_rect(source_rect, exit_x, exit_y)
    if math.isnan(entry_x) or math.isnan(entry_y):
        target_point = automatic_anchor(source_rect, target_rect, False)
    else:
        target_point = point_on_rect(target_rect, entry_x, entry_y)

    result = [source_point]
    geom = edge.find("mxGeometry")
    if geom is not None:
        array = geom.find("Array[@as='points']")
        if array is not None:
            for point in array.findall("mxPoint"):
                try:
                    result.append((float(point.get("x", "0")), float(point.get("y", "0"))))
                except ValueError:
                    pass
    if len(result) == 1:
        sx, sy = source_point
        tx, ty = target_point
        if abs(sx - tx) > abs(sy - ty):
            mid_x = (sx + tx) / 2
            result.extend([(mid_x, sy), (mid_x, ty)])
        else:
            mid_y = (sy + ty) / 2
            result.extend([(sx, mid_y), (tx, mid_y)])
    result.append(target_point)
    return result


def segment_intersects_rect(
    p1: tuple[float, float], p2: tuple[float, float], rect: tuple[float, float, float, float], inset: float = 4
) -> bool:
    x, y, width, height = rect
    left, right = x + inset, x + width - inset
    top, bottom = y + inset, y + height - inset
    x1, y1 = p1
    x2, y2 = p2
    if abs(x1 - x2) < 0.001:
        if not (left <= x1 <= right):
            return False
        lo, hi = sorted((y1, y2))
        return max(lo, top) <= min(hi, bottom)
    if abs(y1 - y2) < 0.001:
        if not (top <= y1 <= bottom):
            return False
        lo, hi = sorted((x1, x2))
        return max(lo, left) <= min(hi, right)
    # Conservative fallback for non-orthogonal segments.
    seg_left, seg_right = sorted((x1, x2))
    seg_top, seg_bottom = sorted((y1, y2))
    return not (seg_right < left or seg_left > right or seg_bottom < top or seg_top > bottom)


def all_segments(points: list[tuple[float, float]]) -> Iterable[tuple[tuple[float, float], tuple[float, float]]]:
    for index in range(len(points) - 1):
        yield points[index], points[index + 1]


def text_plain(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)


def estimated_text_fit(value: str, rect: tuple[float, float, float, float], font_size: float) -> bool:
    _, _, width, height = rect
    chars_per_line = max(4, int(width / max(1.0, font_size * 0.56)))
    needed_lines = 0
    for line in value.split("\n"):
        needed_lines += max(1, math.ceil(max(1, len(line)) / chars_per_line))
    available_lines = max(1, int(height / max(1.0, font_size * 1.28)))
    return needed_lines <= available_lines


def main() -> None:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    path = args.drawio.expanduser().resolve()
    try:
        root = load_xml_root(path)
    except XmlSafetyError as exc:
        raise SystemExit(f"FAIL {exc}") from exc

    valid_aws4_shapes, catalog_version = load_aws4_catalog(args.aws4_catalog.expanduser().resolve())

    if root.tag != "mxfile":
        errors.append("root is not mxfile")
    model = root.find(".//mxGraphModel")
    if model is None:
        errors.append("mxGraphModel is missing")
        page_width = page_height = 0.0
    else:
        page_width = float(model.get("pageWidth", "0"))
        page_height = float(model.get("pageHeight", "0"))
        if page_width < 1200 or page_height < 675:
            errors.append(f"page is below the quality minimum: {page_width:g}x{page_height:g}")

    cells = root.findall(".//mxCell")
    ids = [cell.get("id") for cell in cells]
    if None in ids or len(ids) != len(set(ids)):
        errors.append("empty or duplicate cell id")
    id_set = set(ids)

    by_kind: dict[str, list[ET.Element]] = {}
    for cell in cells:
        by_kind.setdefault(cell.get("data-kind", ""), []).append(cell)

    cards = by_kind.get("resource-card", [])
    icons = by_kind.get("resource-icon", [])
    labels = by_kind.get("resource-label", [])
    edges = by_kind.get("relationship", [])
    captions = by_kind.get("relationship-caption", [])
    titles = by_kind.get("title", [])
    metadata_cells = by_kind.get("diagram-metadata", [])

    if not cards:
        errors.append("no resource cards")
    if len(titles) != 1:
        errors.append(f"expected one title, found {len(titles)}")
    if len(metadata_cells) != 1:
        errors.append(f"expected one diagram metadata cell, found {len(metadata_cells)}")
    elif not (metadata_cells[0].get("data-alt-text") or "").strip():
        warnings.append("draw.io metadata has no alt_text")

    card_ids = {c.get("data-resource-id") for c in cards}
    label_ids = {c.get("data-resource-id") for c in labels}
    if card_ids != label_ids:
        errors.append("resource-card and resource-label IDs differ")

    icon_by_resource = {c.get("data-resource-id"): c for c in icons}
    native_count = 0
    unverified_count = 0
    official_count = 0
    for card in cards:
        resource_id = card.get("data-resource-id")
        provider = card.get("data-provider", "aws")
        icon_required = card.get("data-icon-required") == "1"
        icon = icon_by_resource.get(resource_id)
        if icon_required and icon is None:
            errors.append(f"missing icon for {resource_id}")
        if provider == "aws" and icon_required:
            if icon is None:
                errors.append(f"AWS resource has no icon: {resource_id}")
                continue
            source = icon.get("data-icon-source", "")
            if icon.get("data-icon-official") == "1":
                official_count += 1
            elif source == "drawio-native-aws4":
                native_count += 1
                if args.require_official_aws_icons:
                    errors.append(f"AWS resource uses draw.io native icon instead of official embedded icon: {resource_id}")
                else:
                    warnings.append(f"AWS resource uses draw.io native icon: {resource_id}")
            else:
                unverified_count += 1
                if not args.allow_unverified_aws_icons:
                    errors.append(f"AWS icon is not verified official/native: {resource_id}")

    styles = "\n".join(cell.get("style") or "" for cell in cells)
    if "labelBackgroundColor" in styles:
        errors.append("labelBackgroundColor is forbidden")
    if re.search(r"https?://|file:/|/home/|/Users/|[A-Za-z]:\\", styles):
        errors.append("external URL or local filesystem path found in styles")

    invalid_aws4_shapes: set[str] = set()
    for cell in cells:
        style = cell.get("style") or ""
        for shape_name in re.findall(r"(?:shape|resIcon)=mxgraph\.aws4\.([a-z0-9_]+)", style):
            if shape_name not in valid_aws4_shapes:
                invalid_aws4_shapes.add(shape_name)
    if invalid_aws4_shapes:
        errors.append(f"invalid AWS4 shape references: {sorted(invalid_aws4_shapes)}")

    for icon in icons:
        style = icon.get("style") or ""
        icon_mode = icon.get("data-icon-mode")
        if icon_mode == "embedded":
            if not re.search(r"image=data:image/(?:png|svg\+xml|jpeg),[A-Za-z0-9+/=]+", style):
                errors.append(f"embedded icon has no valid data URI: {icon.get('id')}")
        elif icon_mode == "native":
            resource_icon = (
                "shape=mxgraph.aws4.resourceIcon" in style
                and "resIcon=mxgraph.aws4." in style
            )
            direct_icon = bool(
                re.search(r"(?:^|;)shape=mxgraph\.aws4\.[a-z0-9_]+(?:;|$)", style)
            ) and "shape=mxgraph.aws4.resourceIcon" not in style
            if not resource_icon and not direct_icon:
                errors.append(f"native icon style is invalid: {icon.get('id')}")
        else:
            errors.append(f"icon mode is missing or unsupported: {icon.get('id')}")

    for kind in TRANSPARENT_TEXT_KINDS:
        for cell in by_kind.get(kind, []):
            style = cell.get("style") or ""
            if style_value(style, "fillColor") != "none" or style_value(style, "strokeColor") != "none":
                errors.append(f"text cell is not transparent: {cell.get('id')} ({kind})")
            font_size = style_float(style, "fontSize", 0)
            minimum = 12 if kind in {"relationship-caption", "legend-label", "footer"} else 15
            if kind == "title":
                minimum = 26
            if font_size < minimum:
                warnings.append(f"text cell font is small: {cell.get('id')} {font_size:g}px")

    card_rects: dict[str, tuple[float, float, float, float]] = {}
    cell_rects: dict[str, tuple[float, float, float, float]] = {}
    for cell in cells:
        cell_id = cell.get("id")
        geom = geometry(cell)
        if cell_id and geom:
            cell_rects[cell_id] = geom
            x, y, width, height = geom
            if cell.get("vertex") == "1" and cell.get("data-kind") != "diagram-metadata":
                if x < -0.01 or y < -0.01 or x + width > page_width + 0.01 or y + height > page_height + 0.01:
                    errors.append(f"cell outside page: {cell_id} {geom}")
        if cell.get("data-kind") == "resource-card" and geom:
            card_rects[cell.get("data-resource-id", "")] = geom

    clearance_errors, clearance_warnings = lint_clearance(root)
    errors.extend(clearance_errors)
    warnings.extend(clearance_warnings)

    for label in labels:
        geom = geometry(label)
        style = label.get("style") or ""
        if geom:
            text = text_plain(label.get("value"))
            font_size = style_float(style, "fontSize", 15)
            if not estimated_text_fit(text, geom, font_size):
                errors.append(f"resource label likely clips: {label.get('id')}")

    caption_by_edge = {caption.get("data-edge-id"): caption for caption in captions}
    for edge in edges:
        edge_id = edge.get("id")
        source = edge.get("source")
        target = edge.get("target")
        if source not in card_ids or target not in card_ids:
            errors.append(f"unknown endpoint on edge {edge_id}")
        style = edge.get("style") or ""
        stroke_width = style_float(style, "strokeWidth", 0)
        if stroke_width < 2:
            warnings.append(f"edge is thinner than 2px: {edge_id}")
        if not style_value(style, "endArrow") or style_value(style, "endArrow") == "none":
            errors.append(f"edge has no arrowhead: {edge_id}")
        resolved_color = edge.get("data-resolved-color")
        style_color = style_value(style, "strokeColor")
        if resolved_color and style_color and resolved_color.upper() != style_color.upper():
            errors.append(f"edge colour metadata/style mismatch: {edge_id}")
        color_mode = edge.get("data-color-mode")
        if color_mode == "source" and source in card_rects:
            source_card = next((card for card in cards if card.get("data-resource-id") == source), None)
            source_accent = source_card.get("data-accent") if source_card is not None else None
            if source_accent and style_color and source_accent.upper() != style_color.upper():
                errors.append(f"source-coloured edge does not match source accent: {edge_id}")
        caption_required = edge.get("data-caption-required") == "1"
        caption = caption_by_edge.get(edge_id)
        if caption_required and caption is None:
            errors.append(f"missing caption for edge {edge_id}")
    edge_ids = {edge.get("id") for edge in edges}
    caption_edge_ids = {caption.get("data-edge-id") for caption in captions}
    unknown_caption_edges = caption_edge_ids - edge_ids
    if unknown_caption_edges:
        errors.append(f"captions reference unknown edges: {sorted(unknown_caption_edges)}")

    missing_refs: list[tuple[str | None, str, str]] = []
    for cell in cells:
        for attr in ("parent", "source", "target"):
            value = cell.get(attr)
            if value and value not in id_set:
                missing_refs.append((cell.get("id"), attr, value))
    if missing_refs:
        errors.append(f"missing references: {missing_refs}")

    # Require a legend when the diagram contains more than one connector visual convention.
    edge_signatures = {
        (edge.get("data-resolved-color"), edge.get("data-dashed"))
        for edge in edges
        if edge.get("data-resolved-color")
    }
    if len(edge_signatures) >= 2 and not by_kind.get("legend-shell"):
        warnings.append("multiple connector conventions are used but no legend is present")

    for warning in dict.fromkeys(warnings):
        print(f"WARN {warning}")
    if errors:
        for error in dict.fromkeys(errors):
            print(f"FAIL {error}")
        raise SystemExit(1)
    if args.strict and warnings:
        raise SystemExit("FAIL warnings present in strict mode")
    print(
        f"PASS drawio={args.drawio} resources={len(cards)} edges={len(edges)} "
        f"official_icons={official_count} native_icons={native_count} unverified_icons={unverified_count} "
        f"warnings={len(dict.fromkeys(warnings))} aws4_catalog={catalog_version} portable=yes"
    )


if __name__ == "__main__":
    main()
