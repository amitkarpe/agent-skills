#!/usr/bin/env python3
"""Draft an evidence-backed diagram spec from discovery.json.

Every discovered resource ends up in exactly one place:
  - a node's `covers` list (drawn, alone or as "N x <type>"), or
  - `coverage.omitted` with a reason (folded detail such as an IAM attachment).

The draft draws no arrows. Discovered relations ("is associated with",
"depends on") are not flows, and unrouted arrows cross cards. They are listed in
`coverage.relation_hints`; turn the ones that matter into captioned, routed
edges. Rename nodes and move cards in the spec, keep `covers` and `coverage`
true, then run the normal two-pass build. `check_coverage.py` proves nothing was
dropped or invented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAX_OVERVIEW_NODES = 16
CARD_W, CARD_H = 270, 100
COL_GAP, ROW_GAP = 50, 30
BAND_X, BAND_LABEL_W, BAND_PAD = 40, 230, 22
TOP, BAND_GAP = 130, 24
PER_ROW = 4
TIER_COLOURS = {
    "edge": ("#F5F0FF", "#8C4FFF"),
    "compute": ("#FFF6EC", "#ED7100"),
    "integration": ("#FFF0F6", "#E7157B"),
    "data": ("#F0F8F1", "#3F8624"),
    "delivery": ("#FBF0FD", "#C925D1"),
    "security": ("#FFF1F2", "#DD344C"),
    "operations": ("#FFF0F6", "#B0084D"),
    "unmapped": ("#F8FAFC", "#64748B"),
}
SECRET_LIKE = [
    (re.compile(r"arn:aws[\w-]*:[^\s]*"), "[arn]"),
    (re.compile(r"\b\d{12}\b"), "[account]"),
    (re.compile(r"\b(?:i|vol|sg|subnet|vpc|ami|eni|snap)-[0-9a-f]{8,17}\b"), "[id]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[ip]"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("discovery", type=Path)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--audience", default="Operations engineers")
    parser.add_argument("--type-map", type=Path, default=ROOT / "assets/discovery-type-map.json")
    parser.add_argument(
        "--scope",
        help="case-insensitive regex on resource name or key; resources outside it are omitted as out of scope",
    )
    parser.add_argument("--scope-reason", default="not part of this diagram's workload")
    parser.add_argument(
        "--scope-types",
        help="regex on resource type, also kept in scope (account-wide services such as AWS::GuardDuty::Detector)",
    )
    parser.add_argument(
        "--scope-follow",
        action="store_true",
        help="also pull in resources directly related to an in-scope resource (can pull in other projects through shared networking)",
    )
    parser.add_argument(
        "--max-cards",
        type=int,
        default=MAX_OVERVIEW_NODES,
        help="merge the largest kinds into 'N x kind' cards until the draft fits this many cards",
    )
    return parser.parse_args()


def slug(text: str) -> str:
    """Stable cell ID; scrubbed like labels because IDs are stored in the .drawio file."""
    for pattern, _replacement in SECRET_LIKE:
        text = pattern.sub("x", text)
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "item"


def safe_label(text: str, limit: int = 30) -> str:
    for pattern, replacement in SECRET_LIKE:
        text = pattern.sub(replacement, text)
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def key_ref(key: str) -> str:
    """Spec-side reference to a discovery key. Raw keys hold IDs and stay in the private discovery file."""
    return "k:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def wrap_name(text: str, width: int = 19, max_lines: int = 2) -> str:
    """Break a resource name at -, _, / or . so it never splits mid-word."""
    text = safe_label(text, 200)
    parts = re.split(r"(?<=[-_/.])", text)
    lines, current = [], ""
    for part in parts:
        while len(part) > width:
            if current:
                lines.append(current)
                current = ""
            lines.append(part[:width])
            part = part[width:]
        if len(current) + len(part) > width:
            lines.append(current)
            current = part
        else:
            current += part
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1] + "…"
    return "\n".join(lines)


def load_type_map(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    index: dict[str, dict[str, Any]] = {}
    for entry in data["types"]:
        config_types = entry.get("config") or []
        for config_type in [config_types] if isinstance(config_types, str) else config_types:
            index[config_type] = entry
        for tf_type in entry.get("terraform", []):
            index[tf_type] = entry
    return data, index


def main() -> None:
    args = parse_args()
    discovery_bytes = args.discovery.read_bytes()
    discovery = json.loads(discovery_bytes)
    type_map, index = load_type_map(args.type_map)
    tier_order = list(type_map["tiers"]) + ["unmapped"]
    tier_labels = dict(type_map["tier_labels"], unmapped="Unmapped types (choose an icon)")

    omitted: list[dict[str, str]] = []
    resources = discovery["resources"]
    if args.scope:
        pattern = re.compile(args.scope, re.IGNORECASE)
        type_pattern = re.compile(args.scope_types) if args.scope_types else None
        in_scope = {
            r["key"]
            for r in resources
            if pattern.search(r["name"])
            or pattern.search(r["key"])
            or (type_pattern and type_pattern.fullmatch(r["type"]))
        }
        if args.scope_follow:
            related: set[str] = set()
            for r in resources:
                targets = {rel["to"] for rel in r.get("relations", [])}
                if r["key"] in in_scope:
                    related |= targets
                elif targets & in_scope:
                    related.add(r["key"])
            in_scope |= related & {r["key"] for r in resources}
        for r in resources:
            if r["key"] not in in_scope:
                omitted.append({"key": key_ref(r["key"]), "type": r["type"], "reason": f"out of scope: {args.scope_reason}"})
        resources = [r for r in resources if r["key"] in in_scope]
    name_folds = [(re.compile(f["pattern"]), f["fold"]) for f in type_map.get("name_folds", [])]
    buckets: "OrderedDict[tuple[str, str, str], list[dict[str, Any]]]" = OrderedDict()
    unmapped_types: set[str] = set()
    for resource in resources:
        entry = index.get(resource["type"])
        fold = next((f for rx, f in name_folds if rx.search(resource["name"])), None)
        fold = fold or (entry.get("fold") if entry else None)
        if fold:
            reason = type_map["fold_reasons"][fold]
            omitted.append({"key": key_ref(resource["key"]), "type": resource["type"], "reason": f"{fold}: {reason}"})
            continue
        if entry is None:
            unmapped_types.add(resource["type"])
            entry = {"label": resource["type"], "tier": "unmapped"}
        buckets.setdefault((resource["group"], entry["tier"], entry["label"]), []).append(
            {"resource": resource, "entry": entry}
        )

    # Draw each resource alone, then merge the largest kinds until the draft fits.
    merged: set[tuple[str, str, str]] = set()

    def card_count() -> int:
        return sum(1 if key in merged else len(members) for key, members in buckets.items())

    while card_count() > args.max_cards:
        candidates = [key for key, members in buckets.items() if key not in merged and len(members) > 1]
        if not candidates:
            break
        merged.add(max(candidates, key=lambda key: len(buckets[key])))

    planned = []
    for key, members in buckets.items():
        group, tier, _label = key
        entry = members[0]["entry"]
        if key in merged:
            planned.append({"group": group, "tier": tier, "entry": entry, "members": members, "count": len(members)})
        else:
            for member in members:
                planned.append({"group": group, "tier": tier, "entry": entry, "members": [member], "count": 1})

    groups_seen = list(OrderedDict.fromkeys(p["group"] for p in planned))
    multi_group = len(groups_seen) > 1
    nodes: list[dict[str, Any]] = []
    spec_groups: list[dict[str, Any]] = []
    key_to_node: dict[str, str] = {}
    used_ids: set[str] = set()
    widest = 1
    for group in groups_seen:
        for tier in tier_order:
            widest = max(widest, min(PER_ROW, sum(1 for p in planned if p["group"] == group and p["tier"] == tier)))
    band_w = BAND_LABEL_W + widest * CARD_W + (widest - 1) * COL_GAP + 2 * BAND_PAD
    page_w = max(1920, band_w + 2 * BAND_X)
    band_x = (page_w - band_w) // 2
    y = TOP
    for group in groups_seen:
        for tier in tier_order:
            row_nodes = [p for p in planned if p["group"] == group and p["tier"] == tier]
            if not row_nodes:
                continue
            rows = (len(row_nodes) + PER_ROW - 1) // PER_ROW
            band_h = rows * CARD_H + (rows - 1) * ROW_GAP + 2 * BAND_PAD
            fill, stroke = TIER_COLOURS.get(tier, TIER_COLOURS["unmapped"])
            label = tier_labels.get(tier, tier)
            if multi_group:
                label = f"{group} · {label}"
            group_id = f"tier-{slug(group)}-{tier}"
            spec_groups.append(
                {
                    "id": group_id,
                    "label": label,
                    "kind": "tier-panel",
                    "geometry": [band_x, y, band_w, band_h],
                    "label_geometry": [band_x + 14, y + 14, BAND_LABEL_W - 30, band_h - 28],
                    "fill": fill,
                    "stroke": stroke,
                    "font_size": 17,
                }
            )
            for position, plan in enumerate(row_nodes):
                row, col = divmod(position, PER_ROW)
                x = band_x + BAND_LABEL_W + BAND_PAD + col * (CARD_W + COL_GAP)
                ny = y + BAND_PAD + row * (CARD_H + ROW_GAP)
                entry = plan["entry"]
                first = plan["members"][0]["resource"]
                if plan["count"] > 1:
                    label_text = f"{plan['count']} × {entry['label']}s"
                    base = f"{group}-{first['type']}-all"
                else:
                    label_text = f"{entry['label']}\n{wrap_name(first['name'])}"
                    base = f"{group}-{first['type']}-{first['name']}"
                node_id = slug(base)
                suffix = 2
                while node_id in used_ids:
                    node_id = f"{slug(base)}-{suffix}"
                    suffix += 1
                used_ids.add(node_id)
                node: dict[str, Any] = {
                    "id": node_id,
                    "label": label_text,
                    "variant": "icon-left",
                    "geometry": [x, ny, CARD_W, CARD_H],
                    "fill": "#FFFFFF",
                    "stroke": stroke,
                    "font_size": 15,
                    "state": "current",
                    "covers": [key_ref(m["resource"]["key"]) for m in plan["members"]],
                }
                if tier == "unmapped":
                    node.update({"provider": "external", "variant": "label-only"})
                else:
                    node["provider"] = "aws"
                    if entry.get("icon_key"):
                        node["icon_key"] = entry["icon_key"]
                    if entry.get("native_icon"):
                        node["native_icon"] = entry["native_icon"]
                nodes.append(node)
                for member in plan["members"]:
                    key_to_node[member["resource"]["key"]] = node_id
            y += band_h + BAND_GAP

    hints: list[dict[str, str]] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for resource in discovery["resources"]:
        source = key_to_node.get(resource["key"])
        if not source:
            continue
        for relation in resource.get("relations", []):
            target = key_to_node.get(relation["to"])
            name = str(relation.get("name", "related to"))
            if not target or target == source or "contain" in name.lower():
                continue
            pair = (source, target, name.lower())
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            hints.append({"source": source, "target": target, "relation": name})

    page_h = max(1080, y + 80)
    drawn = sum(len(n["covers"]) for n in nodes)
    tiers_used = list(OrderedDict.fromkeys(tier_labels[p["tier"]].lower() for p in planned))
    alt_text = (
        f"Current state of {', '.join(groups_seen)} built from read-only discovery: "
        f"{drawn} resources drawn as {len(nodes)} cards in {', '.join(tiers_used)}; "
        f"{len(omitted)} low-level resources are listed in the coverage record."
    )[:500]
    spec = {
        "id": slug(args.title),
        "name": args.title,
        "title": args.title,
        "subtitle": args.subtitle or f"Discovered {discovery.get('collected_at', '')[:10]} · draft from discovery",
        "alt_text": alt_text,
        "architecture_type": "current-state",
        "audience": args.audience,
        "status": "current",
        "source_evidence": [
            f"read-only discovery {args.discovery.name} collected {discovery.get('collected_at', 'unknown')}",
            *[f"{s['kind']} input for {s['group']}: {s['resources']} resources" for s in discovery.get("sources", [])],
        ],
        "page": {"width": page_w, "height": page_h, "background": "#FFFFFF"},
        "icon_mode": "auto",
        "edge_color_mode": "source",
        "groups": spec_groups,
        "nodes": nodes,
        "edges": [],
        "legend": "auto",
        "coverage": {
            "discovery": args.discovery.name,
            "discovery_sha256": hashlib.sha256(discovery_bytes).hexdigest(),
            "omitted": omitted,
            "relation_hints": hints,
        },
    }
    args.spec.parent.mkdir(parents=True, exist_ok=True)
    args.spec.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"PASS draft spec={args.spec} resources={len(discovery['resources'])} drawn={drawn} "
        f"cards={len(nodes)} omitted={len(omitted)} relation_hints={len(hints)}"
    )
    if unmapped_types:
        print("WARN unmapped types drawn as label-only cards: " + ", ".join(sorted(unmapped_types)))
    if len(nodes) > args.max_cards:
        print(f"WARN {len(nodes)} cards is above {args.max_cards}; narrow --scope or split by group or tier")


if __name__ == "__main__":
    main()
