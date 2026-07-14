#!/usr/bin/env python3
"""Generate portable, editable draw.io XML from an evidence-backed JSON spec."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EDGE_STYLES: dict[str, tuple[str, bool]] = {
    "request": ("#1E3A5F", False),
    "data": ("#0F766E", False),
    "event": ("#7C3AED", True),
    "control": ("#E8790C", True),
    "security": ("#DC2626", True),
    "observability": ("#C2185B", True),
    "replication": ("#6D28D9", True),
    "planned": ("#9333EA", True),
}

GROUP_STYLES: dict[str, tuple[str, str, str, bool]] = {
    "aws-cloud": ("#FBFCFE", "#64748B", "#334155", False),
    "account": ("#FFFBEB", "#D97706", "#92400E", False),
    "region": ("#F8FAFC", "#94A3B8", "#334155", False),
    "vpc": ("#F7FBF7", "#2E7D32", "#1B5E20", False),
    "availability-zone": ("#FFFFFF", "#2563EB", "#1D4ED8", True),
    "public-subnet": ("#F0F8F1", "#2E7D32", "#1B5E20", False),
    "private-app-subnet": ("#EFF6FF", "#2563EB", "#1E40AF", False),
    "private-db-subnet": ("#F5F3FF", "#6D28D9", "#4C1D95", False),
    "security": ("#FFF1F2", "#E11D48", "#9F1239", True),
    "operations": ("#FDF2F8", "#C2185B", "#9D174D", True),
    "external": ("#F8FAFC", "#64748B", "#334155", False),
    "tier-panel": ("#F8FAFC", "#64748B", "#334155", False),
}

ALLOWED_ICON_MODES = {"auto", "official", "native", "fallback", "none"}
ALLOWED_VARIANTS = {"icon-above", "icon-left", "label-only"}


@dataclass(frozen=True)
class ResolvedIcon:
    mode: str
    key: str
    source: str
    official: bool
    release: str
    path: Path | None = None
    native_name: str | None = None
    native_fill: str | None = None
    native_shape: str = "resource"


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--official-icons", type=Path, default=root / "assets/aws-official/current")
    parser.add_argument("--fallback-icons", type=Path, default=root / "assets/fallback-icons")
    parser.add_argument("--native-map", type=Path, default=root / "assets/native-aws4-map.json")
    parser.add_argument("--allow-bundled-fallback", action="store_true")
    parser.add_argument("--allow-native", action="store_true", default=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def color(value: str | None, default: str, *, allow_none: bool = True) -> str:
    result = default if value is None else str(value)
    if allow_none and result.lower() == "none":
        return "none"
    if not re.fullmatch(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?(?:[0-9A-Fa-f]{2})?", result):
        raise ValueError(f"invalid color: {result!r}")
    return result.upper()


def escape_label(value: Any) -> str:
    return str(value).replace("\n", "<br>")


def data_uri(path: Path) -> str:
    extension = path.suffix.lower()
    mime = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(extension) or mimetypes.guess_type(path.name)[0]
    if not mime or not mime.startswith("image/"):
        raise ValueError(f"unsupported icon type: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    # draw.io style strings use semicolons as property separators. A standard
    # data:*;base64 URI is therefore truncated by the style parser. draw.io's
    # image shape accepts the proven comma form and decodes the payload.
    return f"data:{mime},{encoded}"


def rect(values: Any, name: str) -> list[int]:
    if not isinstance(values, list) or len(values) != 4:
        raise ValueError(f"{name} geometry must contain four values")
    return [int(v) for v in values]


def node_geometry(node: dict[str, Any], layout: dict[str, Any]) -> list[int]:
    if "geometry" in node:
        return rect(node["geometry"], f"node {node.get('id')}")
    if "grid" not in node or not isinstance(node["grid"], list) or len(node["grid"]) != 2:
        raise ValueError(f"node {node.get('id')} needs geometry or grid")
    column, row = [int(value) for value in node["grid"]]
    width = int(node.get("width", layout.get("card_width", 240)))
    height = int(node.get("height", layout.get("card_height", 100)))
    x = int(layout.get("origin_x", 90)) + column * (width + int(layout.get("column_gap", 80)))
    y = int(layout.get("origin_y", 180)) + row * (height + int(layout.get("row_gap", 80)))
    return [x, y, width, height]


class IconResolver:
    def __init__(
        self,
        official_root: Path,
        fallback_root: Path,
        native_map_path: Path,
        allow_fallback: bool,
        allow_native: bool,
        default_mode: str,
    ) -> None:
        self.official_root = official_root.expanduser().resolve()
        self.fallback_root = fallback_root.expanduser().resolve()
        self.allow_fallback = allow_fallback
        self.allow_native = allow_native
        self.default_mode = default_mode
        if default_mode not in ALLOWED_ICON_MODES:
            raise ValueError(f"unsupported icon mode: {default_mode}")
        self.catalog: dict[str, Any] | None = None
        catalog_path = self.official_root / "catalog.json"
        if catalog_path.is_file():
            self.catalog = load_json(catalog_path)
        self.native_map: dict[str, str] = {}
        self.native_direct_shapes: dict[str, str] = {}
        self.native_fill_colors: dict[str, str] = {}
        if native_map_path.is_file():
            native_data = load_json(native_map_path)
            lookup = native_data.get("lookup", {})
            if isinstance(lookup, dict):
                self.native_map = {str(k): str(v) for k, v in lookup.items()}
            direct_shapes = native_data.get("direct_shapes", {})
            if isinstance(direct_shapes, dict):
                self.native_direct_shapes = {str(k): str(v) for k, v in direct_shapes.items()}
            fill_colors = native_data.get("fill_colors", {})
            if isinstance(fill_colors, dict):
                self.native_fill_colors = {
                    str(k): color(str(v), "#5F6B7A", allow_none=False)
                    for k, v in fill_colors.items()
                }

    def _official(self, icon_key: str) -> ResolvedIcon | None:
        if not self.catalog:
            return None
        relative = self.catalog.get("lookup", {}).get(icon_key)
        if not relative:
            return None
        path = (self.official_root / relative).resolve()
        if self.official_root not in path.parents or not path.is_file():
            raise ValueError(f"official icon path is invalid for {icon_key}: {path}")
        return ResolvedIcon(
            mode="embedded",
            path=path,
            key=icon_key,
            source="official-aws-package",
            official=bool(self.catalog.get("official", True)),
            release=str(self.catalog.get("release", "unknown")),
        )

    def _native(self, icon_key: str | None, native_name: str | None) -> ResolvedIcon | None:
        if not self.allow_native:
            return None
        mapped_name = self.native_map.get(icon_key) if icon_key else None
        direct_name = self.native_direct_shapes.get(icon_key) if icon_key else None
        name = native_name or mapped_name or direct_name
        if not name:
            return None
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise ValueError(f"invalid native AWS4 icon name: {name!r}")
        return ResolvedIcon(
            mode="native",
            path=None,
            native_name=name,
            key=icon_key or name,
            source="drawio-native-aws4",
            official=False,
            release="drawio-bundled",
            native_fill=self.native_fill_colors.get(name, "#5F6B7A"),
            native_shape="direct" if direct_name and not native_name and not mapped_name else "resource",
        )

    def _fallback(self, provider: str, icon_key: str | None, icon_file: str | None) -> ResolvedIcon | None:
        if not icon_file:
            return None
        if provider == "aws" and not self.allow_fallback:
            return None
        path = (self.fallback_root / icon_file).resolve()
        if self.fallback_root not in path.parents or not path.is_file():
            raise ValueError(f"fallback/vendor icon is missing or outside asset root: {icon_file}")
        return ResolvedIcon(
            mode="embedded",
            path=path,
            key=icon_key or path.stem,
            source="bundled-fallback" if provider == "aws" else "vendor-local",
            official=False,
            release="bundled",
        )

    def resolve(self, node: dict[str, Any]) -> ResolvedIcon | None:
        provider = str(node.get("provider", "aws"))
        mode = str(node.get("icon_mode", self.default_mode)).lower()
        if mode not in ALLOWED_ICON_MODES:
            raise ValueError(f"unsupported icon mode on {node.get('id')}: {mode}")
        if mode == "none" or node.get("variant") == "label-only":
            return None

        icon_key = str(node.get("icon_key")) if node.get("icon_key") else None
        native_name = str(node.get("native_icon")) if node.get("native_icon") else None
        icon_file = str(node.get("icon")) if node.get("icon") else None

        if provider not in {"aws", "external", "vendor"}:
            raise ValueError(f"unsupported provider on {node.get('id')}: {provider}")

        if provider == "aws":
            if mode in {"official", "auto"} and icon_key:
                resolved = self._official(icon_key)
                if resolved and resolved.official:
                    return resolved
                if mode == "official":
                    if not self.catalog:
                        raise ValueError("official AWS icon catalog is missing; run prepare_aws_icons.py")
                    if resolved and not resolved.official:
                        raise ValueError(
                            "AWS icon catalog is not verified official; rebuild it from the AWS Architecture Icons package"
                        )
                    raise ValueError(f"official AWS icon key not found: {icon_key}")
            if mode in {"native", "auto"}:
                resolved = self._native(icon_key, native_name)
                if resolved:
                    return resolved
                if mode == "native":
                    raise ValueError(f"native AWS4 mapping is missing for node {node.get('id')}")
            if mode in {"fallback", "auto"}:
                resolved = self._fallback(provider, icon_key, icon_file)
                if resolved:
                    return resolved
            raise ValueError(
                f"AWS node has no resolvable icon: {node.get('id')}; prepare official icons or provide a tested native_icon"
            )

        return self._fallback(provider, icon_key, icon_file)


def main() -> None:
    args = parse_args()
    spec = load_json(args.spec)
    output = args.output.expanduser().resolve()
    default_icon_mode = str(spec.get("icon_mode", "auto")).lower()
    resolver = IconResolver(
        args.official_icons,
        args.fallback_icons,
        args.native_map,
        args.allow_bundled_fallback,
        args.allow_native,
        default_icon_mode,
    )

    page = spec.get("page", {})
    layout = spec.get("layout", {})
    page_width = int(page.get("width", 1920))
    page_height = int(page.get("height", 1080))
    background = color(page.get("background"), "#FFFFFF")
    default_edge_color_mode = str(spec.get("edge_color_mode", "source")).lower()
    if default_edge_color_mode not in {"source", "target", "semantic", "explicit"}:
        raise ValueError(f"unsupported edge_color_mode: {default_edge_color_mode}")
    alt_text = " ".join(str(spec.get("alt_text", "")).split())
    long_description = " ".join(str(spec.get("long_description", "")).split())

    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "agent": "aws-architecture-diagram-skill-v2",
            "version": "2",
            "type": "device",
        },
    )
    diagram = ET.SubElement(
        mxfile,
        "diagram",
        {
            "id": str(spec.get("id", "aws-architecture")),
            "name": str(spec.get("name", "AWS Architecture")),
            "data-alt-text": alt_text,
            "data-long-description": long_description,
        },
    )
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": str(page_width),
            "dy": str(page_height),
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(page_width),
            "pageHeight": str(page_height),
            "background": background,
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    ids = {"0", "1"}

    def reserve(cell_id: str) -> None:
        if not cell_id or cell_id in ids:
            raise ValueError(f"duplicate or empty cell id: {cell_id!r}")
        ids.add(cell_id)

    def vertex(cell_id: str, value: str, geometry: list[int], style: str, **extra: str) -> ET.Element:
        reserve(cell_id)
        attrs = {"id": cell_id, "value": value, "style": style, "vertex": "1", "parent": "1", **extra}
        cell = ET.SubElement(root, "mxCell", attrs)
        x, y, width, height = geometry
        ET.SubElement(
            cell,
            "mxGeometry",
            {"x": str(x), "y": str(y), "width": str(width), "height": str(height), "as": "geometry"},
        )
        return cell

    def edge_cell(
        cell_id: str,
        source: str | None,
        target: str | None,
        style: str,
        points: list[list[int]] | None = None,
        source_point: tuple[int, int] | None = None,
        target_point: tuple[int, int] | None = None,
        **extra: str,
    ) -> ET.Element:
        reserve(cell_id)
        attrs: dict[str, str] = {"id": cell_id, "value": "", "style": style, "edge": "1", "parent": "1", **extra}
        if source:
            attrs["source"] = source
        if target:
            attrs["target"] = target
        cell = ET.SubElement(root, "mxCell", attrs)
        geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if source_point:
            ET.SubElement(geom, "mxPoint", {"x": str(source_point[0]), "y": str(source_point[1]), "as": "sourcePoint"})
        if target_point:
            ET.SubElement(geom, "mxPoint", {"x": str(target_point[0]), "y": str(target_point[1]), "as": "targetPoint"})
        if points:
            array = ET.SubElement(geom, "Array", {"as": "points"})
            for point in points:
                ET.SubElement(array, "mxPoint", {"x": str(int(point[0])), "y": str(int(point[1]))})
        return cell

    def transparent_text_style(
        *,
        align: str = "left",
        valign: str = "middle",
        font_size: int = 15,
        font_color: str = "#172033",
        font_style: int = 0,
    ) -> str:
        return (
            "text;html=1;strokeColor=none;fillColor=none;whiteSpace=wrap;overflow=hidden;"
            f"align={align};verticalAlign={valign};fontFamily=Arial;fontSize={font_size};"
            f"fontStyle={font_style};fontColor={font_color};"
        )

    # Metadata cell for validation and provenance.
    vertex(
        "diagram-metadata",
        "",
        [0, 0, 1, 1],
        "shape=rectangle;fillColor=none;strokeColor=none;opacity=0;",
        **{
            "data-kind": "diagram-metadata",
            "data-schema-version": "3",
            "data-icon-mode": default_icon_mode,
            "data-edge-color-mode": default_edge_color_mode,
            "data-theme": str(spec.get("theme", "aws-clean-2026")),
            "data-alt-text": alt_text,
            "data-long-description": long_description,
        },
    )

    boundary_labels: list[tuple[str, str, list[int], str, str, str]] = []
    boundary = spec.get("boundary")
    if boundary:
        kind = str(boundary.get("kind", "aws-cloud"))
        default_fill, default_stroke, default_font, default_dashed = GROUP_STYLES.get(kind, GROUP_STYLES["aws-cloud"])
        geometry = rect(boundary.get("geometry"), f"boundary {boundary.get('id')}")
        fill = color(boundary.get("fill"), default_fill)
        stroke = color(boundary.get("stroke"), default_stroke)
        dashed = bool(boundary.get("dashed", default_dashed))
        shell_style = (
            "rounded=1;absoluteArcSize=1;arcSize=36;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth={float(boundary.get('stroke_width', 2.2))};"
        )
        if dashed:
            shell_style += "dashed=1;dashPattern=8 6;"
        vertex(
            str(boundary["id"]),
            "",
            geometry,
            shell_style,
            **{"data-kind": "boundary-shell", "data-boundary-kind": kind, "data-accent": stroke},
        )
        x, y, width, _ = geometry
        label_geometry = rect(boundary.get("label_geometry", [x + 24, y + 24, width - 48, 30]), "boundary label")
        boundary_labels.append((f"{boundary['id']}-label", escape_label(boundary["label"]), label_geometry, default_font, str(boundary.get("label_align", "left")), str(boundary["id"])))

    group_labels: list[tuple[str, str, list[int], str, str, int, str]] = []
    group_accents: dict[str, str] = {}
    for group in spec.get("groups", []):
        kind = str(group.get("kind", "external"))
        default_fill, default_stroke, default_font, default_dashed = GROUP_STYLES.get(kind, GROUP_STYLES["external"])
        geometry = rect(group.get("geometry"), f"group {group.get('id')}")
        fill = color(group.get("fill"), default_fill)
        stroke = color(group.get("stroke"), default_stroke)
        group_accents[str(group["id"])] = stroke
        dashed = bool(group.get("dashed", default_dashed))
        shell_style = (
            "rounded=1;arcSize=8;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth={float(group.get('stroke_width', 2))};"
        )
        if dashed:
            shell_style += "dashed=1;dashPattern=8 6;"
        vertex(
            str(group["id"]),
            "",
            geometry,
            shell_style,
            **{"data-kind": "group-shell", "data-group-kind": kind, "data-accent": stroke},
        )
        x, y, width, height = geometry
        label_align = str(group.get("label_align", "center" if kind in {"availability-zone", "tier-panel"} else "left"))
        if kind == "tier-panel":
            default_label_geometry = [x + 12, y + 16, width - 24, height - 32]
            default_font_size = 18
        else:
            default_label_geometry = [x + 14, y + 8, width - 28, 30]
            default_font_size = 16
        label_geometry = rect(group.get("label_geometry", default_label_geometry), f"group label {group.get('id')}")
        group_labels.append(
            (
                f"{group['id']}-label",
                escape_label(group["label"]),
                label_geometry,
                color(group.get("font_color"), default_font),
                label_align,
                int(group.get("font_size", default_font_size)),
                str(group["id"]),
            )
        )

    nodes = spec.get("nodes", [])
    node_rects: dict[str, list[int]] = {}
    node_icons: dict[str, ResolvedIcon | None] = {}
    node_accents: dict[str, str] = {}
    node_variants: dict[str, str] = {}

    for node in nodes:
        node_id = str(node["id"])
        geometry = node_geometry(node, layout)
        node_rects[node_id] = geometry
        variant = str(node.get("variant", "icon-left"))
        if variant not in ALLOWED_VARIANTS:
            raise ValueError(f"unsupported node variant on {node_id}: {variant}")
        node_variants[node_id] = variant
        icon = resolver.resolve(node)
        node_icons[node_id] = icon
        provider = str(node.get("provider", "aws"))
        state = str(node.get("state", "current"))
        state_stroke = {"planned": "#9333EA", "deprecated": "#DC2626", "unknown": "#D97706"}.get(state, "#CBD5E1")
        stroke = color(node.get("stroke"), state_stroke)
        fill = color(node.get("fill"), "#FFFFFF")
        accent = color(node.get("accent"), stroke if stroke != "none" else "#334155")
        node_accents[node_id] = accent
        dash = "dashed=1;dashPattern=8 6;" if state in {"planned", "unknown"} else ""
        card_style = (
            "rounded=1;arcSize=10;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth={float(node.get('stroke_width', 1.6))};{dash}"
            f"shadow={1 if bool(node.get('shadow', False)) else 0};"
        )
        data_attrs = {
            "data-kind": "resource-card",
            "data-resource-id": node_id,
            "data-provider": provider,
            "data-state": state,
            "data-accent": accent,
            "data-icon-required": "1" if icon else "0",
            "data-variant": variant,
        }
        if icon:
            data_attrs.update(
                {
                    "data-icon-key": icon.key,
                    "data-icon-source": icon.source,
                    "data-icon-official": "1" if icon.official else "0",
                    "data-icon-release": icon.release,
                    "data-icon-mode": icon.mode,
                }
            )
        vertex(node_id, "", geometry, card_style, **data_attrs)

    # Connectors are below icons and labels.
    caption_specs: list[tuple[dict[str, Any], list[int], str]] = []
    edge_kinds_used: list[str] = []
    edge_visuals: list[tuple[str, str, bool]] = []
    for edge in spec.get("edges", []):
        edge_id = str(edge["id"])
        source = str(edge["source"])
        target = str(edge["target"])
        if source not in node_rects or target not in node_rects:
            raise ValueError(f"edge {edge_id} has unknown endpoint: {source}->{target}")
        kind = str(edge.get("kind", "request"))
        semantic_color, default_dashed = EDGE_STYLES.get(kind, EDGE_STYLES["request"])
        color_mode = str(edge.get("color_mode", default_edge_color_mode)).lower()
        # A supplied colour is an explicit override unless the caller deliberately
        # declares another mode. This keeps metadata and rendered style consistent.
        if edge.get("color") and "color_mode" not in edge:
            color_mode = "explicit"
        if color_mode == "source":
            resolved_color = node_accents[source]
        elif color_mode == "target":
            resolved_color = node_accents[target]
        elif color_mode == "semantic":
            resolved_color = semantic_color
        elif color_mode == "explicit":
            if not edge.get("color"):
                raise ValueError(f"edge {edge_id} uses explicit color mode without color")
            resolved_color = color(edge.get("color"), semantic_color)
        else:
            raise ValueError(f"edge {edge_id} has unsupported color mode: {color_mode}")
        if edge.get("color") and color_mode != "explicit":
            resolved_color = color(edge.get("color"), resolved_color)
        dashed = bool(edge.get("dashed", default_dashed))
        stroke_width = float(edge.get("stroke_width", 2.7 if not dashed else 2.3))
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
            f"strokeWidth={stroke_width};endArrow=block;endFill=1;endSize=9;strokeColor={resolved_color};"
            "exitPerimeter=1;entryPerimeter=1;"
        )
        if dashed:
            style += "dashed=1;dashPattern=8 6;"
        for key in ("exitX", "exitY", "entryX", "entryY"):
            if key in edge:
                style += f"{key}={edge[key]};"
        points = edge.get("points")
        edge_cell(
            edge_id,
            source,
            target,
            style,
            points=points,
            **{
                "data-kind": "relationship",
                "data-edge-kind": kind,
                "data-color-mode": color_mode,
                "data-resolved-color": resolved_color,
                "data-dashed": "1" if dashed else "0",
                "data-caption-required": "1" if edge.get("caption") else "0",
            },
        )
        edge_kinds_used.append(kind)
        edge_visuals.append((resolved_color, dashed, kind))
        caption = edge.get("caption")
        if caption:
            caption_geometry = edge.get("caption_geometry")
            if not caption_geometry:
                sx, sy, sw, sh = node_rects[source]
                tx, ty, tw, th = node_rects[target]
                mid_x = int(((sx + sw / 2) + (tx + tw / 2)) / 2 - 90)
                mid_y = int(((sy + sh / 2) + (ty + th / 2)) / 2 - 14)
                caption_geometry = [mid_x, mid_y, 180, 28]
            caption_specs.append((edge, rect(caption_geometry, f"caption {edge_id}"), resolved_color))
        elif not edge.get("unlabeled_reason"):
            raise ValueError(f"edge {edge_id} needs caption or unlabeled_reason")

    # Resource icons and transparent labels.
    for node in nodes:
        node_id = str(node["id"])
        x, y, width, height = node_rects[node_id]
        icon = node_icons[node_id]
        variant = node_variants[node_id]
        icon_size = int(node.get("icon_size", 58 if variant == "icon-above" else 52))
        if node.get("icon_geometry"):
            icon_geometry = rect(node["icon_geometry"], f"icon {node_id}")
        elif variant == "icon-above":
            icon_geometry = [x + int((width - icon_size) / 2), y + 8, icon_size, icon_size]
        elif variant == "icon-left":
            icon_geometry = [x + 16, y + int((height - icon_size) / 2), icon_size, icon_size]
        else:
            icon_geometry = [x, y, 0, 0]

        if icon:
            if icon.mode == "embedded" and icon.path:
                icon_style = (
                    "shape=image;imageAspect=0;aspect=fixed;verticalLabelPosition=bottom;verticalAlign=top;"
                    f"image={data_uri(icon.path)};"
                )
            elif icon.mode == "native" and icon.native_name:
                # draw.io AWS4 resourceIcon stencils are monochrome. The category
                # colour must be supplied through fillColor and the inner glyph/
                # border uses white. Omitting fillColor produces faint/invisible
                # icons in Draw.io Desktop.
                native_fill = color(
                    str(node.get("icon_fill")) if node.get("icon_fill") else icon.native_fill,
                    "#5F6B7A",
                    allow_none=False,
                )
                if icon.native_shape == "direct":
                    icon_style = (
                        f"shape=mxgraph.aws4.{icon.native_name};aspect=fixed;html=1;"
                        f"fillColor={native_fill};strokeColor=none;pointerEvents=1;"
                    )
                else:
                    icon_style = (
                        "shape=mxgraph.aws4.resourceIcon;aspect=fixed;html=1;"
                        f"resIcon=mxgraph.aws4.{icon.native_name};fillColor={native_fill};strokeColor=#FFFFFF;"
                        "points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],"
                        "[0,0.25,0],[1,0.25,0],[0,0.5,0],[1,0.5,0],[0,0.75,0],"
                        "[1,0.75,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0]];"
                    )
            else:
                raise ValueError(f"unsupported icon resolution for {node_id}")
            vertex(
                f"{node_id}-icon",
                "",
                icon_geometry,
                icon_style,
                **{
                    "data-kind": "resource-icon",
                    "data-resource-id": node_id,
                    "data-provider": str(node.get("provider", "aws")),
                    "data-icon-key": icon.key,
                    "data-icon-source": icon.source,
                    "data-icon-official": "1" if icon.official else "0",
                    "data-icon-release": icon.release,
                    "data-icon-mode": icon.mode,
                    "data-native-icon": icon.native_name or "",
                },
            )

        if node.get("label_geometry"):
            label_geometry = rect(node["label_geometry"], f"label {node_id}")
        elif variant == "icon-above":
            label_geometry = [x + 4, y + icon_size + 14, width - 8, max(28, height - icon_size - 18)]
        elif variant == "icon-left" and icon:
            label_geometry = [x + icon_size + 30, y + 10, width - icon_size - 44, height - 20]
        else:
            label_geometry = [x + 12, y + 10, width - 24, height - 20]
        align = str(node.get("align", "center" if variant == "icon-above" else "left"))
        valign = str(node.get("vertical_align", "middle"))
        font_size = int(node.get("font_size", 15))
        font_color = color(node.get("font_color"), "#172033")
        font_style = int(node.get("font_style", 1))
        vertex(
            f"{node_id}-label",
            escape_label(node["label"]),
            label_geometry,
            transparent_text_style(
                align=align,
                valign=valign,
                font_size=font_size,
                font_color=font_color,
                font_style=font_style,
            ),
            **{
                "data-kind": "resource-label",
                "data-resource-id": node_id,
                "data-provider": str(node.get("provider", "aws")),
            },
        )

    # Transparent connector captions.
    for edge, geometry, resolved_color in caption_specs:
        vertex(
            f"{edge['id']}-caption",
            escape_label(edge["caption"]),
            geometry,
            transparent_text_style(
                align=str(edge.get("caption_align", "center")),
                valign="middle",
                font_size=int(edge.get("font_size", 13)),
                font_color=color(edge.get("caption_color"), resolved_color),
                font_style=int(edge.get("font_style", 1)),
            ),
            **{"data-kind": "relationship-caption", "data-edge-id": str(edge["id"])},
        )

    # Boundary and group labels are above connectors.
    for label_id, value, geometry, font_color, align, boundary_id in boundary_labels:
        vertex(
            label_id,
            value,
            geometry,
            transparent_text_style(align=align, valign="middle", font_size=18, font_color=font_color, font_style=1),
            **{"data-kind": "boundary-label", "data-boundary-id": boundary_id},
        )
    for label_id, value, geometry, font_color, align, font_size, group_id in group_labels:
        vertex(
            label_id,
            value,
            geometry,
            transparent_text_style(align=align, valign="middle", font_size=font_size, font_color=font_color, font_style=1),
            **{"data-kind": "group-label", "data-group-id": group_id},
        )

    for annotation in spec.get("annotations", []):
        geometry = rect(annotation.get("geometry"), f"annotation {annotation.get('id')}")
        if annotation.get("box"):
            style = (
                "rounded=1;arcSize=8;whiteSpace=wrap;html=1;"
                f"fillColor={color(annotation.get('fill'), '#FFFFFF')};"
                f"strokeColor={color(annotation.get('stroke'), '#CBD5E1')};strokeWidth=1;"
                f"align={annotation.get('align', 'center')};verticalAlign=middle;fontFamily=Arial;"
                f"fontSize={int(annotation.get('font_size', 14))};fontStyle={int(annotation.get('font_style', 0))};"
                f"fontColor={color(annotation.get('color'), '#475569')};"
            )
        else:
            style = transparent_text_style(
                align=str(annotation.get("align", "center")),
                valign=str(annotation.get("vertical_align", "middle")),
                font_size=int(annotation.get("font_size", 14)),
                font_color=color(annotation.get("color"), "#475569"),
                font_style=int(annotation.get("font_style", 0)),
            )
        vertex(
            str(annotation["id"]),
            escape_label(annotation["text"]),
            geometry,
            style,
            **{"data-kind": "annotation"},
        )

    # Title and subtitle.
    title_geometry = rect(spec.get("title_geometry", [120, 22, page_width - 240, 44]), "title")
    vertex(
        "title",
        escape_label(spec.get("title", "AWS Architecture")),
        title_geometry,
        transparent_text_style(align="center", valign="middle", font_size=30, font_color="#172033", font_style=1),
        **{"data-kind": "title"},
    )
    subtitle = spec.get("subtitle", "")
    if subtitle:
        subtitle_geometry = rect(spec.get("subtitle_geometry", [180, 74, page_width - 360, 30]), "subtitle")
        vertex(
            "subtitle",
            escape_label(subtitle),
            subtitle_geometry,
            transparent_text_style(align="center", valign="middle", font_size=16, font_color="#475569", font_style=0),
            **{"data-kind": "subtitle"},
        )

    # Explicit or automatic legend.
    legend = spec.get("legend", False)
    explicit_legend = isinstance(legend, dict) and bool(legend.get("show", True))
    auto_legend = legend is True or legend == "auto"
    if explicit_legend:
        legend_geometry = rect(legend.get("geometry", [page_width - 390, page_height - 260, 330, 200]), "legend")
        lx, ly, lw, lh = legend_geometry
        vertex(
            "legend-box",
            "",
            legend_geometry,
            "rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#CBD5E1;strokeWidth=1.2;",
            **{"data-kind": "legend-shell"},
        )
        vertex(
            "legend-title",
            escape_label(legend.get("title", "Legend")),
            [lx + 16, ly + 10, lw - 32, 26],
            transparent_text_style(align="left", valign="middle", font_size=15, font_color="#334155", font_style=1),
            **{"data-kind": "legend-title", "data-legend-id": "legend-box"},
        )
        item_y = ly + 44
        for index, item in enumerate(legend.get("items", [])):
            item_type = str(item.get("type", "line"))
            item_id = f"legend-item-{index + 1}"
            if item_type == "box":
                vertex(
                    f"{item_id}-swatch",
                    "",
                    [lx + 18, item_y + 3, 34, 18],
                    "rounded=1;arcSize=4;"
                    f"fillColor={color(item.get('fill'), '#F8FAFC')};"
                    f"strokeColor={color(item.get('stroke'), '#64748B')};strokeWidth=1.5;",
                    **{"data-kind": "legend-swatch", "data-legend-id": "legend-box", "data-legend-item-id": item_id},
                )
            elif item_type == "line":
                line_color = color(item.get("color"), "#334155")
                line_style = f"endArrow=block;endFill=1;endSize=8;strokeWidth=2.4;strokeColor={line_color};"
                if item.get("dashed"):
                    line_style += "dashed=1;dashPattern=8 6;"
                edge_cell(
                    f"{item_id}-line",
                    None,
                    None,
                    line_style,
                    source_point=(lx + 18, item_y + 12),
                    target_point=(lx + 54, item_y + 12),
                    **{"data-kind": "legend-line", "data-legend-id": "legend-box", "data-legend-item-id": item_id},
                )
            else:
                raise ValueError(f"unsupported legend item type: {item_type}")
            vertex(
                f"{item_id}-label",
                escape_label(item.get("label", "")),
                [lx + 66, item_y, lw - 82, 24],
                transparent_text_style(align="left", valign="middle", font_size=13, font_color="#475569", font_style=0),
                **{"data-kind": "legend-label", "data-legend-id": "legend-box", "data-legend-item-id": item_id},
            )
            item_y += 32
    elif auto_legend:
        unique_visuals: list[tuple[str, bool, str]] = []
        seen_conventions: set[tuple[str, bool]] = set()
        for line_color, dashed, kind in edge_visuals:
            convention = (kind, dashed)
            if convention in seen_conventions:
                continue
            seen_conventions.add(convention)
            semantic_color = EDGE_STYLES.get(kind, (line_color, dashed))[0]
            unique_visuals.append((semantic_color, dashed, kind))
        if len(unique_visuals) >= 2:
            lx = int(spec.get("legend_x", page_width - 380))
            ly = int(spec.get("legend_y", page_height - 60 - (48 + 30 * len(unique_visuals))))
            lw = 320
            lh = 48 + 30 * len(unique_visuals)
            vertex(
                "legend-box",
                "",
                [lx, ly, lw, lh],
                "rounded=1;arcSize=8;fillColor=#FFFFFF;strokeColor=#CBD5E1;strokeWidth=1.2;",
                **{"data-kind": "legend-shell"},
            )
            vertex(
                "legend-title",
                "Legend",
                [lx + 16, ly + 10, lw - 32, 24],
                transparent_text_style(align="left", valign="middle", font_size=15, font_color="#334155", font_style=1),
                **{"data-kind": "legend-title", "data-legend-id": "legend-box"},
            )
            for index, (line_color, dashed, kind) in enumerate(unique_visuals):
                item_y = ly + 42 + index * 32
                style = f"endArrow=block;endFill=1;endSize=8;strokeWidth=2.4;strokeColor={line_color};"
                if dashed:
                    style += "dashed=1;dashPattern=8 6;"
                edge_cell(
                    f"legend-{index + 1}-line",
                    None,
                    None,
                    style,
                    source_point=(lx + 18, item_y + 12),
                    target_point=(lx + 58, item_y + 12),
                    **{"data-kind": "legend-line", "data-legend-id": "legend-box", "data-legend-item-id": f"legend-{index + 1}"},
                )
                vertex(
                    f"legend-{index + 1}-label",
                    kind.replace("-", " ").title(),
                    [lx + 72, item_y, lw - 88, 24],
                    transparent_text_style(align="left", valign="middle", font_size=13, font_color="#475569", font_style=0),
                    **{"data-kind": "legend-label", "data-legend-id": "legend-box", "data-legend-item-id": f"legend-{index + 1}"},
                )

    footer = spec.get("footer")
    if footer:
        if isinstance(footer, dict):
            footer_text = " · ".join(str(footer.get(key)) for key in ("status", "owner", "date", "note") if footer.get(key))
        else:
            footer_text = str(footer)
        vertex(
            "footer",
            escape_label(footer_text),
            [70, page_height - 38, page_width - 140, 22],
            transparent_text_style(align="left", valign="middle", font_size=12, font_color="#64748B", font_style=0),
            **{"data-kind": "footer"},
        )

    ET.indent(mxfile, space="  ")
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(mxfile).write(output, encoding="utf-8", xml_declaration=True)
    print(output)


if __name__ == "__main__":
    main()
