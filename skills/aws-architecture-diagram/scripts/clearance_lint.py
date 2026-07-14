#!/usr/bin/env python3
"""Pure, non-mutating layout-clearance checks for generated draw.io XML."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import defusedxml.ElementTree as ET

DEFAULT_CLEARANCE = 8.0
HARD_CLEARANCE = 1.0

PROTECTED_RECT_KINDS = {
    "annotation",
    "boundary-label",
    "footer",
    "group-label",
    "legend-label",
    "legend-swatch",
    "legend-title",
    "relationship-caption",
    "resource-card",
    "resource-icon",
    "resource-label",
    "subtitle",
    "title",
}

EDGE_PROTECTED_KINDS = PROTECTED_RECT_KINDS | {"legend-shell"}


@dataclass(frozen=True)
class ProtectedRect:
    cell_id: str
    kind: str
    rect: tuple[float, float, float, float]
    resource_id: str = ""
    edge_id: str = ""
    legend_id: str = ""
    legend_item_id: str = ""


def geometry(cell: ET.Element) -> tuple[float, float, float, float] | None:
    item = cell.find("mxGeometry")
    if item is None:
        return None
    try:
        return tuple(float(item.get(key, "0")) for key in ("x", "y", "width", "height"))
    except ValueError:
        return None


def rectangle_gap(
    left: tuple[float, float, float, float], right: tuple[float, float, float, float]
) -> float:
    lx, ly, lw, lh = left
    rx, ry, rw, rh = right
    dx = max(rx - (lx + lw), lx - (rx + rw), 0.0)
    dy = max(ry - (ly + lh), ly - (ry + rh), 0.0)
    return math.hypot(dx, dy)


def segment_rect_gap(
    start: tuple[float, float], end: tuple[float, float], rect: tuple[float, float, float, float]
) -> float:
    x, y, width, height = rect
    left, right, top, bottom = x, x + width, y, y + height
    x1, y1 = start
    x2, y2 = end
    if abs(y1 - y2) < 0.001:
        seg_left, seg_right = sorted((x1, x2))
        dx = max(left - seg_right, seg_left - right, 0.0)
        dy = max(top - y1, y1 - bottom, 0.0)
        return math.hypot(dx, dy)
    if abs(x1 - x2) < 0.001:
        seg_top, seg_bottom = sorted((y1, y2))
        dx = max(left - x1, x1 - right, 0.0)
        dy = max(top - seg_bottom, seg_top - bottom, 0.0)
        return math.hypot(dx, dy)
    seg_box = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    return rectangle_gap(seg_box, rect)


def all_segments(points: list[tuple[float, float]]) -> Iterable[tuple[tuple[float, float], tuple[float, float]]]:
    for index in range(len(points) - 1):
        yield points[index], points[index + 1]


def point_on_rect(rect: tuple[float, float, float, float], rx: float, ry: float) -> tuple[float, float]:
    x, y, width, height = rect
    return x + width * rx, y + height * ry


def style_float(style: str, key: str) -> float | None:
    for item in style.split(";"):
        if item.startswith(key + "="):
            try:
                return float(item.split("=", 1)[1])
            except ValueError:
                return None
    return None


def automatic_anchor(
    source: tuple[float, float, float, float], target: tuple[float, float, float, float], source_side: bool
) -> tuple[float, float]:
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


def anchor_axis(rx: float | None, ry: float | None, start: tuple[float, float], end: tuple[float, float]) -> str:
    """Resolve whether a connector must initially travel horizontally or vertically."""
    if rx is not None and ry is not None:
        x_border = abs(rx) < 0.001 or abs(rx - 1.0) < 0.001
        y_border = abs(ry) < 0.001 or abs(ry - 1.0) < 0.001
        if x_border and not y_border:
            return "horizontal"
        if y_border and not x_border:
            return "vertical"
    return "horizontal" if abs(end[0] - start[0]) >= abs(end[1] - start[1]) else "vertical"


def edge_points(
    edge: ET.Element, cards: dict[str, tuple[float, float, float, float]]
) -> list[tuple[float, float]]:
    source_id, target_id = edge.get("source", ""), edge.get("target", "")
    if source_id not in cards or target_id not in cards:
        return []
    source, target = cards[source_id], cards[target_id]
    style = edge.get("style") or ""
    exit_x, exit_y = style_float(style, "exitX"), style_float(style, "exitY")
    entry_x, entry_y = style_float(style, "entryX"), style_float(style, "entryY")
    source_point = (
        point_on_rect(source, exit_x, exit_y)
        if exit_x is not None and exit_y is not None
        else automatic_anchor(source, target, True)
    )
    target_point = (
        point_on_rect(target, entry_x, entry_y)
        if entry_x is not None and entry_y is not None
        else automatic_anchor(source, target, False)
    )
    points = [source_point]
    geom = edge.find("mxGeometry")
    if geom is not None:
        array = geom.find("Array[@as='points']")
        if array is not None:
            for point in array.findall("mxPoint"):
                try:
                    points.append((float(point.get("x", "0")), float(point.get("y", "0"))))
                except ValueError:
                    continue
    if len(points) == 1:
        sx, sy = source_point
        tx, ty = target_point
        source_axis = anchor_axis(exit_x, exit_y, source_point, target_point)
        target_axis = anchor_axis(entry_x, entry_y, target_point, source_point)
        if source_axis == target_axis == "horizontal":
            middle = (sx + tx) / 2
            points.extend(((middle, sy), (middle, ty)))
        elif source_axis == target_axis == "vertical":
            middle = (sy + ty) / 2
            points.extend(((sx, middle), (tx, middle)))
        elif source_axis == "vertical":
            points.append((sx, ty))
        else:
            points.append((tx, sy))
    points.append(target_point)
    return points


def related(left: ProtectedRect, right: ProtectedRect) -> bool:
    if left.resource_id and left.resource_id == right.resource_id:
        return True
    if left.legend_item_id and left.legend_item_id == right.legend_item_id:
        return True
    return False


def classify_gap(subject: str, other: str, gap: float) -> tuple[str, str] | None:
    diagnostic = f"clearance {subject} vs {other} gap={gap:.2f}px"
    if gap < HARD_CLEARANCE:
        return "error", diagnostic
    if gap < DEFAULT_CLEARANCE:
        return "warning", diagnostic
    return None


def point_on_border(point: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
    px, py = point
    x, y, width, height = rect
    inside_x = x - 0.01 <= px <= x + width + 0.01
    inside_y = y - 0.01 <= py <= y + height + 0.01
    on_vertical = abs(px - x) < 0.01 or abs(px - (x + width)) < 0.01
    on_horizontal = abs(py - y) < 0.01 or abs(py - (y + height)) < 0.01
    return (inside_y and on_vertical) or (inside_x and on_horizontal)


def departs_rect(
    endpoint: tuple[float, float], other: tuple[float, float], rect: tuple[float, float, float, float]
) -> bool:
    """Return true only when a segment leaves a declared border directly outward."""
    if not point_on_border(endpoint, rect):
        return False
    px, py = endpoint
    ox, oy = other
    x, y, width, height = rect
    epsilon = 0.01
    return any(
        (
            abs(px - x) < epsilon and ox < px - epsilon,
            abs(px - (x + width)) < epsilon and ox > px + epsilon,
            abs(py - y) < epsilon and oy < py - epsilon,
            abs(py - (y + height)) < epsilon and oy > py + epsilon,
        )
    )


def lint_clearance(root: ET.Element) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    cells = root.findall(".//mxCell")
    by_id = {cell.get("id", ""): cell for cell in cells}
    protected: list[ProtectedRect] = []
    for cell in cells:
        kind = cell.get("data-kind", "")
        rect = geometry(cell)
        if kind in EDGE_PROTECTED_KINDS and rect:
            protected.append(
                ProtectedRect(
                    cell.get("id", ""),
                    kind,
                    rect,
                    cell.get("data-resource-id", ""),
                    cell.get("data-edge-id", ""),
                    cell.get("data-legend-id", ""),
                    cell.get("data-legend-item-id", ""),
                )
            )

    pairwise = [item for item in protected if item.kind in PROTECTED_RECT_KINDS]
    for index, left in enumerate(pairwise):
        for right in pairwise[index + 1 :]:
            if related(left, right):
                continue
            result = classify_gap(left.cell_id, right.cell_id, rectangle_gap(left.rect, right.rect))
            if result:
                (errors if result[0] == "error" else warnings).append(result[1])

    for label_kind, shell_kind, owner_attr, minimum_inset in (
        ("boundary-label", "boundary-shell", "data-boundary-id", 24.0),
        ("group-label", "group-shell", "data-group-id", 8.0),
    ):
        shells = {cell.get("id", ""): geometry(cell) for cell in cells if cell.get("data-kind") == shell_kind}
        for label in (cell for cell in cells if cell.get("data-kind") == label_kind):
            owner = label.get(owner_attr, "")
            label_rect, shell_rect = geometry(label), shells.get(owner)
            if not label_rect or not shell_rect:
                errors.append(f"clearance {label.get('id')} has no declared {shell_kind} owner {owner}")
                continue
            lx, ly, lw, lh = label_rect
            sx, sy, sw, sh = shell_rect
            insets = (lx - sx, ly - sy, sx + sw - (lx + lw), sy + sh - (ly + lh))
            required = (minimum_inset, minimum_inset, DEFAULT_CLEARANCE, DEFAULT_CLEARANCE)
            for side, actual, expected in zip(("left", "top", "right", "bottom"), insets, required):
                if actual < expected:
                    errors.append(
                        f"clearance {label.get('id')} to {owner} {side}-border gap={actual:.2f}px required={expected:.2f}px"
                    )

    cards = {
        cell.get("id", ""): geometry(cell)
        for cell in cells
        if cell.get("data-kind") == "resource-card" and geometry(cell)
    }
    for edge in (cell for cell in cells if cell.get("data-kind") == "relationship"):
        edge_id = edge.get("id", "")
        source, target = edge.get("source", ""), edge.get("target", "")
        points = edge_points(edge, cards)  # type: ignore[arg-type]
        segments = list(all_segments(points))
        for item in protected:
            for segment_index, (start, end) in enumerate(segments):
                if (
                    item.kind == "resource-card"
                    and item.cell_id == source
                    and segment_index == 0
                    and departs_rect(start, end, item.rect)
                ):
                    continue
                if (
                    item.kind == "resource-card"
                    and item.cell_id == target
                    and segment_index == len(segments) - 1
                    and departs_rect(end, start, item.rect)
                ):
                    continue
                gap = segment_rect_gap(start, end, item.rect)
                result = classify_gap(edge_id, item.cell_id, gap)
                if result:
                    (errors if result[0] == "error" else warnings).append(result[1])
                    break

    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))
