#!/usr/bin/env python3
"""Search the bundled AWS4 draw.io shape registry without MCP or network access."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+", help="Service or resource words, for example: parameter store")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--category")
    parser.add_argument("--catalog", type=Path, default=root / "assets/aws4-shapes.json")
    return parser.parse_args()


def normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower().replace("_", " ")))


def match_score(query: str, shape: str, category: str) -> int:
    shape_text = normalize(shape)
    category_text = normalize(category)
    shape_tokens = set(shape_text.split())
    category_tokens = set(category_text.split())
    combined_tokens = shape_tokens | category_tokens
    tokens = set(query.split())
    if shape_text == query:
        return 100
    if query in shape_text:
        return 85
    if tokens <= combined_tokens:
        return 65 + sum(5 for token in tokens if token in shape_tokens)
    if len(tokens) > 1:
        return 0
    return sum(8 for token in tokens if token in combined_tokens)


def result_style(shape: str, kind: str, fill: str | None) -> str:
    if kind == "direct":
        fill_style = f"fillColor={fill};" if fill else ""
        return f"shape=mxgraph.aws4.{shape};aspect=fixed;html=1;{fill_style}"
    fill_style = f"fillColor={fill};" if fill else ""
    return (
        "shape=mxgraph.aws4.resourceIcon;aspect=fixed;html=1;"
        f"resIcon=mxgraph.aws4.{shape};{fill_style}strokeColor=#FFFFFF;"
    )


def main() -> None:
    args = parse_args()
    if args.limit < 1 or args.limit > 100:
        raise SystemExit("FAIL --limit must be between 1 and 100")
    data: dict[str, Any] = json.loads(args.catalog.read_text(encoding="utf-8"))
    query = normalize(" ".join(args.query))
    category_filter = normalize(args.category) if args.category else None
    matches_by_shape: dict[str, dict[str, Any]] = {}

    for category, details in data["categories"].items():
        if category_filter and normalize(category) != category_filter:
            continue
        raw_fill = details.get("fillColor")
        fill = raw_fill if isinstance(raw_fill, str) and raw_fill.startswith("#") else None
        for shape in details.get("shapes", []):
            score = match_score(query, str(shape), str(category))
            if score <= 0:
                continue
            kind = "direct" if category in {"sub_resources", "groups"} else "resourceIcon"
            candidate = {
                "shape": str(shape),
                "category": str(category),
                "kind": kind,
                "fillColor": fill,
                "score": score,
                "style": result_style(str(shape), kind, fill),
            }
            current = matches_by_shape.get(str(shape))
            if current is None or (candidate["score"], candidate["category"]) > (
                current["score"],
                current["category"],
            ):
                matches_by_shape[str(shape)] = candidate

    matches = list(matches_by_shape.values())
    matches.sort(key=lambda item: (-item["score"], item["shape"], item["category"]))
    output = {
        "query": query,
        "catalog_version": str(data.get("version", "unknown")),
        "generated_from": str(data.get("generated_from", "unknown")),
        "results": matches[: args.limit],
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
