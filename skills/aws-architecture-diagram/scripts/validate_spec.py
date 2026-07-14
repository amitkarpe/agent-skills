#!/usr/bin/env python3
"""Validate AWS architecture JSON specifications before XML generation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ARCHITECTURE_TYPES = {
    "overview",
    "application",
    "deployment",
    "integration",
    "network",
    "devops",
    "security",
    "data-flow",
    "current-state",
    "target-state",
}
EDGE_KINDS = {"request", "data", "event", "control", "security", "observability", "replication", "planned"}
EDGE_COLOR_MODES = {"source", "target", "semantic", "explicit"}
ICON_MODES = {"auto", "official", "native", "fallback", "none"}
VARIANTS = {"icon-above", "icon-left", "label-only"}
ALT_TEXT_MIN_LENGTH = 40
ALT_TEXT_MAX_LENGTH = 500
ALT_TEXT_PLACEHOLDERS = {
    "alt text",
    "architecture diagram",
    "aws architecture diagram",
    "diagram",
    "placeholder",
    "tbd",
    "todo",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    return parser.parse_args()


def geometry_values(item: dict[str, Any], name: str) -> tuple[int, int, int, int]:
    values = item.get("geometry")
    if not isinstance(values, list) or len(values) != 4:
        raise ValueError(f"{name} geometry must have four values")
    try:
        return tuple(int(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} geometry contains a non-integer value") from exc


def geometry_for(node: dict[str, Any], layout: dict[str, Any]) -> tuple[int, int, int, int]:
    if "geometry" in node:
        return geometry_values(node, f"node {node.get('id')}")
    if "grid" not in node or not isinstance(node["grid"], list) or len(node["grid"]) != 2:
        raise ValueError(f"node {node.get('id')} needs geometry or grid")
    column, row = [int(value) for value in node["grid"]]
    width = int(node.get("width", layout.get("card_width", 240)))
    height = int(node.get("height", layout.get("card_height", 100)))
    x = int(layout.get("origin_x", 90)) + column * (width + int(layout.get("column_gap", 80)))
    y = int(layout.get("origin_y", 180)) + row * (height + int(layout.get("row_gap", 80)))
    return x, y, width, height


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int], padding: int = 0) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax - padding < bx + bw + padding
        and ax + aw + padding > bx - padding
        and ay - padding < by + bh + padding
        and ay + ah + padding > by - padding
    )


def inside_page(rect: tuple[int, int, int, int], page_width: int, page_height: int) -> bool:
    x, y, width, height = rect
    return x >= 0 and y >= 0 and width > 0 and height > 0 and x + width <= page_width and y + height <= page_height


def estimated_text_fit(text: str, geometry: tuple[int, int, int, int], font_size: int) -> tuple[bool, str]:
    _, _, width, height = geometry
    if width <= 0 or height <= 0:
        return False, "non-positive label geometry"
    explicit_lines = str(text).split("\n")
    chars_per_line = max(4, int(width / max(1.0, font_size * 0.56)))
    required_lines = 0
    for line in explicit_lines:
        required_lines += max(1, math.ceil(max(1, len(line)) / chars_per_line))
    available_lines = max(1, int(height / max(1.0, font_size * 1.28)))
    return required_lines <= available_lines, f"requires about {required_lines} lines; space allows about {available_lines}"


def validate_accessibility(spec: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    alt_text = spec.get("alt_text")
    if alt_text is None:
        warnings.append("legacy spec has no alt_text; add architecture-specific accessibility text")
    elif not isinstance(alt_text, str) or not alt_text.strip():
        errors.append("alt_text must be a non-empty string")
    else:
        normalized = " ".join(alt_text.split())
        lowered = normalized.casefold().rstrip(".")
        if lowered in ALT_TEXT_PLACEHOLDERS or "lorem ipsum" in lowered:
            errors.append("alt_text is placeholder text")
        if len(normalized) < ALT_TEXT_MIN_LENGTH:
            errors.append(
                f"alt_text is too short: {len(normalized)} characters; minimum is {ALT_TEXT_MIN_LENGTH}"
            )
        if len(normalized) > ALT_TEXT_MAX_LENGTH:
            errors.append(
                f"alt_text is too long: {len(normalized)} characters; maximum is {ALT_TEXT_MAX_LENGTH}"
            )

    long_description = spec.get("long_description")
    if long_description is not None and (
        not isinstance(long_description, str) or not long_description.strip()
    ):
        errors.append("long_description must be a non-empty string when provided")


def label_geometry_for(node: dict[str, Any], rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if "label_geometry" in node:
        return geometry_values({"geometry": node["label_geometry"]}, f"label {node.get('id')}")
    x, y, width, height = rect
    variant = str(node.get("variant", "icon-left"))
    icon_size = int(node.get("icon_size", 58 if variant == "icon-above" else 52))
    if variant == "icon-above":
        return x + 4, y + icon_size + 14, width - 8, max(28, height - icon_size - 18)
    if variant == "icon-left":
        return x + icon_size + 30, y + 10, width - icon_size - 44, height - 20
    return x + 12, y + 10, width - 24, height - 20


def main() -> None:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(spec, dict):
        raise SystemExit("FAIL JSON root must be an object")

    validate_accessibility(spec, errors, warnings)

    for key in ("id", "name", "title"):
        if not spec.get(key):
            errors.append(f"missing top-level field: {key}")

    architecture_type = str(spec.get("architecture_type", "overview")).lower()
    if architecture_type not in ARCHITECTURE_TYPES:
        errors.append(f"unsupported architecture_type: {architecture_type}")
    if not spec.get("audience"):
        warnings.append("audience is not declared")
    if not spec.get("source_evidence"):
        warnings.append("source_evidence is empty; architecture truth may be unclear")

    icon_mode = str(spec.get("icon_mode", "auto")).lower()
    if icon_mode not in ICON_MODES:
        errors.append(f"unsupported icon_mode: {icon_mode}")
    default_edge_color_mode = str(spec.get("edge_color_mode", "source")).lower()
    if default_edge_color_mode not in EDGE_COLOR_MODES:
        errors.append(f"unsupported edge_color_mode: {default_edge_color_mode}")

    page = spec.get("page", {})
    page_width = int(page.get("width", 1920))
    page_height = int(page.get("height", 1080))
    if page_width < 1200 or page_height < 675:
        errors.append(f"page is too small for the default quality contract: {page_width}x{page_height}")

    nodes = spec.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        errors.append("no nodes defined")
        nodes = []
    if len(nodes) > 25:
        warnings.append(f"diagram has {len(nodes)} nodes; split into overview/detail views")
    elif len(nodes) > 16 and architecture_type == "overview":
        warnings.append(f"overview has {len(nodes)} nodes; target 5-12 and maximum 16")

    all_ids: set[str] = set()
    node_ids: set[str] = set()
    rectangles: dict[str, tuple[int, int, int, int]] = {}
    label_rectangles: dict[str, tuple[int, int, int, int]] = {}

    def add_id(item_id: str, kind: str) -> None:
        if not item_id:
            errors.append(f"empty {kind} id")
        elif item_id in all_ids:
            errors.append(f"duplicate id: {item_id}")
        else:
            all_ids.add(item_id)

    boundary = spec.get("boundary")
    if boundary:
        add_id(str(boundary.get("id", "")), "boundary")
        try:
            boundary_rect = geometry_values(boundary, "boundary")
            if not inside_page(boundary_rect, page_width, page_height):
                errors.append(f"boundary is outside page: {boundary_rect}")
        except ValueError as exc:
            errors.append(str(exc))

    for group in spec.get("groups", []):
        group_id = str(group.get("id", ""))
        add_id(group_id, "group")
        try:
            group_rect = geometry_values(group, f"group {group_id}")
            if not inside_page(group_rect, page_width, page_height):
                errors.append(f"group {group_id} is outside page: {group_rect}")
            if group_rect[2] < 120 or group_rect[3] < 60:
                warnings.append(f"group {group_id} may be too small: {group_rect[2]}x{group_rect[3]}")
        except ValueError as exc:
            errors.append(str(exc))

    layout = spec.get("layout", {})
    for node in nodes:
        node_id = str(node.get("id", ""))
        add_id(node_id, "node")
        node_ids.add(node_id)
        provider = str(node.get("provider", "aws"))
        variant = str(node.get("variant", "icon-left"))
        node_icon_mode = str(node.get("icon_mode", icon_mode)).lower()
        if variant not in VARIANTS:
            errors.append(f"node {node_id} has unsupported variant: {variant}")
        if node_icon_mode not in ICON_MODES:
            errors.append(f"node {node_id} has unsupported icon_mode: {node_icon_mode}")
        if not node.get("label"):
            errors.append(f"node {node_id} has no label")
        if provider == "aws" and variant != "label-only" and node_icon_mode != "none":
            if node_icon_mode == "official" and not node.get("icon_key"):
                errors.append(f"AWS node {node_id} in official mode needs icon_key")
            elif node_icon_mode == "native" and not node.get("native_icon") and not node.get("icon_key"):
                errors.append(f"AWS node {node_id} in native mode needs native_icon or mapped icon_key")
            elif node_icon_mode == "auto" and not (node.get("icon_key") or node.get("native_icon") or node.get("icon")):
                errors.append(f"AWS node {node_id} needs icon_key, native_icon, or explicit fallback icon")
        try:
            node_rect = geometry_for(node, layout)
            rectangles[node_id] = node_rect
            if not inside_page(node_rect, page_width, page_height):
                errors.append(f"node {node_id} is outside page bounds: {node_rect}")
            width, height = node_rect[2], node_rect[3]
            minimum_width = 120 if variant == "icon-above" else 160
            minimum_height = 90 if variant == "icon-above" else 76
            if width < minimum_width or height < minimum_height:
                warnings.append(f"node {node_id} may be too small for {variant}: {width}x{height}")
            label_rect = label_geometry_for(node, node_rect)
            label_rectangles[node_id] = label_rect
            if not inside_page(label_rect, page_width, page_height):
                errors.append(f"label for {node_id} is outside page: {label_rect}")
            font_size = int(node.get("font_size", 15))
            if font_size < 15:
                warnings.append(f"node {node_id} font size {font_size}px is below the 15px quality target")
            fits, reason = estimated_text_fit(str(node.get("label", "")), label_rect, font_size)
            if not fits:
                errors.append(f"node {node_id} label likely clips: {reason}")
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))

    node_list = list(rectangles)
    for index, left_id in enumerate(node_list):
        for right_id in node_list[index + 1 :]:
            if overlaps(rectangles[left_id], rectangles[right_id], padding=2):
                errors.append(f"resource endpoints overlap: {left_id} and {right_id}")

    edge_visual_signatures: set[tuple[str, bool]] = set()
    for edge in spec.get("edges", []):
        edge_id = str(edge.get("id", ""))
        add_id(edge_id, "edge")
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source not in node_ids or target not in node_ids:
            errors.append(f"edge {edge_id} has unknown endpoint")
        kind = str(edge.get("kind", "request"))
        if kind not in EDGE_KINDS:
            errors.append(f"edge {edge_id} has unsupported kind: {kind}")
        color_mode = str(edge.get("color_mode", default_edge_color_mode)).lower()
        if color_mode not in EDGE_COLOR_MODES:
            errors.append(f"edge {edge_id} has unsupported color_mode: {color_mode}")
        if color_mode == "explicit" and not edge.get("color"):
            errors.append(f"edge {edge_id} uses explicit color mode without color")
        if not edge.get("caption") and not edge.get("unlabeled_reason"):
            errors.append(f"edge {edge_id} needs caption or unlabeled_reason")
        if edge.get("points"):
            points = edge["points"]
            if not isinstance(points, list) or any(not isinstance(point, list) or len(point) != 2 for point in points):
                errors.append(f"edge {edge_id} points must be a list of [x, y] pairs")
        if edge.get("caption_geometry"):
            try:
                caption_rect = geometry_values({"geometry": edge["caption_geometry"]}, f"caption {edge_id}")
                if not inside_page(caption_rect, page_width, page_height):
                    errors.append(f"caption {edge_id} is outside page: {caption_rect}")
                for node_id, node_rect in rectangles.items():
                    if overlaps(caption_rect, node_rect) and not edge.get("allow_caption_overlap"):
                        errors.append(f"caption {edge_id} overlaps resource endpoint {node_id}")
            except ValueError as exc:
                errors.append(str(exc))
        elif edge.get("caption") and source in rectangles and target in rectangles:
            sx, sy, sw, sh = rectangles[source]
            tx, ty, tw, th = rectangles[target]
            distance = math.hypot((sx + sw / 2) - (tx + tw / 2), (sy + sh / 2) - (ty + th / 2))
            if distance > 420:
                warnings.append(f"long edge {edge_id} has no explicit caption_geometry")
            if distance > 500 and not edge.get("points"):
                warnings.append(f"long edge {edge_id} has no explicit waypoints")
        dashed = bool(edge.get("dashed", kind in {"event", "control", "security", "observability", "replication", "planned"}))
        edge_visual_signatures.add((color_mode if color_mode != "explicit" else str(edge.get("color")), dashed))

    for annotation in spec.get("annotations", []):
        annotation_id = str(annotation.get("id", ""))
        add_id(annotation_id, "annotation")
        try:
            annotation_rect = geometry_values(annotation, f"annotation {annotation_id}")
            if not inside_page(annotation_rect, page_width, page_height):
                errors.append(f"annotation {annotation_id} is outside page: {annotation_rect}")
        except ValueError as exc:
            errors.append(str(exc))

    legend = spec.get("legend", "auto")
    if legend is False and len(edge_visual_signatures) >= 2:
        warnings.append("legend is disabled despite multiple connector styles")
    if isinstance(legend, dict) and legend.get("show", True):
        try:
            legend_rect = geometry_values(legend, "legend")
            if not inside_page(legend_rect, page_width, page_height):
                errors.append(f"legend is outside page: {legend_rect}")
            if not legend.get("items"):
                warnings.append("explicit legend has no items")
        except ValueError as exc:
            errors.append(str(exc))

    for warning in warnings:
        print(f"WARN {warning}")
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        raise SystemExit(1)
    if args.strict and warnings:
        raise SystemExit("FAIL warnings present in strict mode")
    print(
        f"PASS spec={args.spec} nodes={len(nodes)} edges={len(spec.get('edges', []))} "
        f"groups={len(spec.get('groups', []))} warnings={len(warnings)}"
    )


if __name__ == "__main__":
    main()
