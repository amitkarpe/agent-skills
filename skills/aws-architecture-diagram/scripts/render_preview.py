#!/usr/bin/env python3
"""Render the skill's supported draw.io XML subset to SVG and PNG for visual review.

This renderer is intentionally limited. It is a layout-review fallback when draw.io
Desktop CLI is unavailable; it is not an exact replacement for draw.io rendering.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import math
import re
from pathlib import Path
from typing import Iterable

import cairosvg
import defusedxml.ElementTree as ET
from xml_safety import XmlSafetyError, load_xml_root

NATIVE_ICON_STYLE = {
    "users": ("USR", "#334155"),
    "route_53": ("53", "#6D28D9"),
    "cloudfront": ("CF", "#6D28D9"),
    "internet_gateway": ("IGW", "#6D28D9"),
    "application_load_balancer": ("ALB", "#6D28D9"),
    "nat_gateway": ("NAT", "#6D28D9"),
    "ec2": ("EC2", "#E8790C"),
    "auto_scaling": ("ASG", "#E8790C"),
    "rds": ("RDS", "#5B3FD1"),
    "s3": ("S3", "#4C8C2B"),
    "cloudwatch": ("CW", "#C2185B"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("drawio", type=Path)
    parser.add_argument("svg", type=Path)
    parser.add_argument("png", type=Path)
    parser.add_argument("--scale", type=float, default=1.0)
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


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def color_or_none(value: str | None, default: str = "none") -> str:
    if not value:
        return default
    if value.lower() == "none":
        return "none"
    return value


def rounded_radius(style: str, width: float, height: float) -> float:
    if style_value(style, "rounded") != "1":
        return 0
    arc = style_float(style, "arcSize", 8)
    if style_value(style, "absoluteArcSize") == "1":
        return max(0.0, arc / 2.0)
    return max(3.0, min(width, height) * arc / 100.0)


def dash_array(style: str) -> str | None:
    if style_value(style, "dashed") != "1":
        return None
    pattern = style_value(style, "dashPattern") or "8 6"
    return pattern.replace(" ", ",")


def rect_svg(cell: ET.Element) -> str:
    geom = geometry(cell)
    if not geom:
        return ""
    x, y, width, height = geom
    style = cell.get("style") or ""
    fill = color_or_none(style_value(style, "fillColor"), "none")
    stroke = color_or_none(style_value(style, "strokeColor"), "none")
    stroke_width = style_float(style, "strokeWidth", 1)
    radius = rounded_radius(style, width, height)
    dash = dash_array(style)
    attrs = [
        f'x="{x:g}"',
        f'y="{y:g}"',
        f'width="{width:g}"',
        f'height="{height:g}"',
        f'rx="{radius:g}"',
        f'ry="{radius:g}"',
        f'fill="{escape(fill)}"',
        f'stroke="{escape(stroke)}"',
        f'stroke-width="{stroke_width:g}"',
    ]
    if dash:
        attrs.append(f'stroke-dasharray="{escape(dash)}"')
    if style_value(style, "opacity") == "0":
        attrs.append('opacity="0"')
    return f"<rect {' '.join(attrs)}/>"


def plain_text(value: str | None) -> list[str]:
    if not value:
        return []
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return [html.unescape(part) for part in text.split("\n")]


def wrap_lines(lines: list[str], width: float, font_size: float) -> list[str]:
    max_chars = max(4, int(width / max(1.0, font_size * 0.56)))
    result: list[str] = []
    for line in lines:
        words = line.split()
        if not words:
            result.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            if len(candidate) <= max_chars:
                current = candidate
            else:
                result.append(current)
                current = word
        while len(current) > max_chars:
            result.append(current[:max_chars])
            current = current[max_chars:]
        result.append(current)
    return result


def text_svg(cell: ET.Element) -> str:
    geom = geometry(cell)
    if not geom:
        return ""
    x, y, width, height = geom
    style = cell.get("style") or ""
    font_size = style_float(style, "fontSize", 15)
    font_color = color_or_none(style_value(style, "fontColor"), "#172033")
    font_weight = "700" if style_value(style, "fontStyle") in {"1", "3"} else "400"
    align = style_value(style, "align") or "left"
    valign = style_value(style, "verticalAlign") or "middle"
    lines = wrap_lines(plain_text(cell.get("value")), width, font_size)
    if not lines:
        return ""
    line_height = font_size * 1.25
    total_height = line_height * len(lines)
    if valign == "top":
        baseline = y + font_size
    elif valign == "bottom":
        baseline = y + height - total_height + font_size
    else:
        baseline = y + (height - total_height) / 2 + font_size
    if align == "center":
        anchor = "middle"
        tx = x + width / 2
    elif align == "right":
        anchor = "end"
        tx = x + width
    else:
        anchor = "start"
        tx = x
    parts = [
        f'<text x="{tx:g}" y="{baseline:g}" fill="{escape(font_color)}" '
        f'font-family="Arial, DejaVu Sans, sans-serif" font-size="{font_size:g}" '
        f'font-weight="{font_weight}" text-anchor="{anchor}">'
    ]
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else line_height
        parts.append(f'<tspan x="{tx:g}" dy="{dy:g}">{escape(line)}</tspan>')
    parts.append("</text>")
    return "".join(parts)


def image_svg(cell: ET.Element) -> str:
    geom = geometry(cell)
    if not geom:
        return ""
    x, y, width, height = geom
    style = cell.get("style") or ""
    data_match = re.search(r"image=(data:image/(?:png|jpeg|svg\+xml);base64,[^;]+)", style)
    if data_match:
        href = data_match.group(1)
        return (
            f'<image x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
            f'preserveAspectRatio="xMidYMid meet" href="{escape(href)}"/>'
        )
    native_match = re.search(r"resIcon=mxgraph\.aws4\.([a-z0-9_]+)", style)
    if native_match:
        name = native_match.group(1)
        abbreviation, icon_color = NATIVE_ICON_STYLE.get(name, (name[:4].upper(), "#64748B"))
        size = min(width, height)
        cx, cy = x + width / 2, y + height / 2
        radius = size * 0.44
        font_size = max(10, min(18, size * 0.24))
        return (
            f'<circle cx="{cx:g}" cy="{cy:g}" r="{radius:g}" fill="#FFFFFF" '
            f'stroke="{icon_color}" stroke-width="3"/>'
            f'<text x="{cx:g}" y="{cy + font_size * 0.36:g}" fill="{icon_color}" '
            f'font-family="Arial, DejaVu Sans, sans-serif" font-size="{font_size:g}" '
            f'font-weight="700" text-anchor="middle">{escape(abbreviation)}</text>'
        )
    return ""


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


def edge_polyline(edge: ET.Element, card_rects: dict[str, tuple[float, float, float, float]]) -> list[tuple[float, float]]:
    geom = edge.find("mxGeometry")
    source_id = edge.get("source")
    target_id = edge.get("target")
    style = edge.get("style") or ""

    if source_id in card_rects and target_id in card_rects:
        source_rect = card_rects[source_id]
        target_rect = card_rects[target_id]
        exit_x = style_float(style, "exitX", math.nan)
        exit_y = style_float(style, "exitY", math.nan)
        entry_x = style_float(style, "entryX", math.nan)
        entry_y = style_float(style, "entryY", math.nan)
        source_point = (
            automatic_anchor(source_rect, target_rect, True)
            if math.isnan(exit_x) or math.isnan(exit_y)
            else point_on_rect(source_rect, exit_x, exit_y)
        )
        target_point = (
            automatic_anchor(source_rect, target_rect, False)
            if math.isnan(entry_x) or math.isnan(entry_y)
            else point_on_rect(target_rect, entry_x, entry_y)
        )
    elif geom is not None:
        source_element = geom.find("mxPoint[@as='sourcePoint']")
        target_element = geom.find("mxPoint[@as='targetPoint']")
        if source_element is None or target_element is None:
            return []
        source_point = (float(source_element.get("x", "0")), float(source_element.get("y", "0")))
        target_point = (float(target_element.get("x", "0")), float(target_element.get("y", "0")))
    else:
        return []

    points = [source_point]
    if geom is not None:
        array = geom.find("Array[@as='points']")
        if array is not None:
            for point in array.findall("mxPoint"):
                points.append((float(point.get("x", "0")), float(point.get("y", "0"))))
    if len(points) == 1:
        sx, sy = source_point
        tx, ty = target_point
        if abs(sx - tx) > abs(sy - ty):
            mid_x = (sx + tx) / 2
            points.extend([(mid_x, sy), (mid_x, ty)])
        else:
            mid_y = (sy + ty) / 2
            points.extend([(sx, mid_y), (tx, mid_y)])
    points.append(target_point)
    return points


def marker_id(color: str) -> str:
    return "arrow-" + hashlib.sha1(color.encode("utf-8")).hexdigest()[:10]


def edge_svg(edge: ET.Element, card_rects: dict[str, tuple[float, float, float, float]], markers: set[str]) -> str:
    points = edge_polyline(edge, card_rects)
    if len(points) < 2:
        return ""
    style = edge.get("style") or ""
    stroke = color_or_none(style_value(style, "strokeColor"), "#334155")
    stroke_width = style_float(style, "strokeWidth", 2)
    dash = dash_array(style)
    marker = marker_id(stroke)
    markers.add(stroke)
    attrs = [
        f'points="{" ".join(f"{x:g},{y:g}" for x, y in points)}"',
        'fill="none"',
        f'stroke="{escape(stroke)}"',
        f'stroke-width="{stroke_width:g}"',
        'stroke-linecap="round"',
        'stroke-linejoin="round"',
        f'marker-end="url(#{marker})"',
    ]
    if dash:
        attrs.append(f'stroke-dasharray="{escape(dash)}"')
    return f"<polyline {' '.join(attrs)}/>"


def main() -> None:
    args = parse_args()
    try:
        root = load_xml_root(args.drawio)
    except XmlSafetyError as exc:
        raise SystemExit(f"FAIL {exc}") from exc
    model = root.find(".//mxGraphModel")
    if model is None:
        raise SystemExit("FAIL mxGraphModel is missing")
    width = float(model.get("pageWidth", "1920"))
    height = float(model.get("pageHeight", "1080"))
    background = model.get("background", "#FFFFFF")
    cells = root.findall(".//mxCell")
    card_rects = {
        cell.get("data-resource-id", ""): geometry(cell)
        for cell in cells
        if cell.get("data-kind") == "resource-card" and geometry(cell)
    }
    card_rects = {key: value for key, value in card_rects.items() if value is not None}

    markers: set[str] = set()
    body: list[str] = [f'<rect width="{width:g}" height="{height:g}" fill="{escape(background)}"/>']

    for cell in cells:
        kind = cell.get("data-kind", "")
        if cell.get("vertex") == "1":
            if kind in {"diagram-metadata"}:
                continue
            if kind in {
                "boundary-shell",
                "group-shell",
                "resource-card",
                "legend-shell",
                "legend-swatch",
            } or (kind == "annotation" and style_value(cell.get("style") or "", "fillColor") not in {None, "none"}):
                body.append(rect_svg(cell))
            elif kind == "resource-icon":
                body.append(image_svg(cell))
            else:
                body.append(text_svg(cell))
        elif cell.get("edge") == "1":
            body.append(edge_svg(cell, card_rects, markers))

    defs = ["<defs>"]
    for stroke in sorted(markers):
        marker = marker_id(stroke)
        defs.append(
            f'<marker id="{marker}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{escape(stroke)}"/></marker>'
        )
    defs.append("</defs>")

    svg_text = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width:g}" height="{height:g}" viewBox="0 0 {width:g} {height:g}">\n'
        + "\n".join(defs)
        + "\n"
        + "\n".join(part for part in body if part)
        + "\n</svg>\n"
    )
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.png.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(svg_text, encoding="utf-8")
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=str(args.png),
        output_width=max(1, int(width * args.scale)),
        output_height=max(1, int(height * args.scale)),
    )
    print(f"PASS preview-svg={args.svg} preview-png={args.png} size={width:g}x{height:g} scale={args.scale:g}")


if __name__ == "__main__":
    main()
