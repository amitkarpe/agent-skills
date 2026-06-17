#!/usr/bin/env python3
"""Validate a static json-render-style report spec against the local component catalog."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SECRET_RE = re.compile(r"(?i)(aws_secret_access_key|secret_access_key|session_token|password\s*=|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})")
EXTERNAL_RE = re.compile(r"(?i)(https?:)?//(?!localhost|127\.0\.0\.1|192\.168\.|100\.)")
ACCOUNT_ID_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
RAW_HTML_RE = re.compile(r"(?is)<\s*(script|style|iframe|object|embed|link|img|svg|html|body|div|span|table|section|article|header|footer)\b")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid json: {path}: {exc}")


def iter_strings(value: Any, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_strings(item, f"{path}.{key}")


def validate(spec: dict[str, Any], catalog: dict[str, Any], allow_account_ids: bool = False) -> list[str]:
    problems: list[str] = []
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]

    for key in ["schema_version", "skill", "title", "root", "elements"]:
        if key not in spec:
            problems.append(f"missing required top-level key: {key}")

    if spec.get("skill") != catalog.get("skill"):
        problems.append(f"spec skill must be {catalog.get('skill')!r}, got {spec.get('skill')!r}")

    elements = spec.get("elements")
    if not isinstance(elements, dict):
        problems.append("elements must be an object/map")
        return problems

    max_elements = int(catalog.get("max_elements", 100))
    if len(elements) > max_elements:
        problems.append(f"too many elements: {len(elements)} > {max_elements}")

    root = spec.get("root")
    if root not in elements:
        problems.append(f"root element {root!r} not found in elements")
    elif not isinstance(elements[root], dict) or elements[root].get("type") != "Page":
        problems.append(f"root element {root!r} must have type 'Page'")

    components = catalog.get("components", {})
    if not isinstance(components, dict):
        problems.append("catalog components must be an object")
        return problems

    for elem_id, elem in elements.items():
        if not isinstance(elem_id, str) or not elem_id:
            problems.append("element ids must be non-empty strings")
            continue
        if not isinstance(elem, dict):
            problems.append(f"element {elem_id}: must be an object")
            continue
        etype = elem.get("type")
        props = elem.get("props")
        children = elem.get("children")
        if etype not in components:
            problems.append(f"element {elem_id}: unknown component type {etype!r}")
            continue
        if not isinstance(props, dict):
            problems.append(f"element {elem_id}: props must be an object")
            continue
        if not isinstance(children, list) or not all(isinstance(child, str) for child in children):
            problems.append(f"element {elem_id}: children must be a string array")
            continue
        for child in children:
            if child not in elements:
                problems.append(f"element {elem_id}: child {child!r} not found")

        cdef = components[etype]
        required = set(cdef.get("required_props", []))
        optional = set(cdef.get("optional_props", []))
        allowed = required | optional
        missing = sorted(required - set(props))
        if missing:
            problems.append(f"element {elem_id} ({etype}): missing required props: {', '.join(missing)}")
        unknown = sorted(set(props) - allowed)
        if unknown:
            problems.append(f"element {elem_id} ({etype}): unknown props: {', '.join(unknown)}")

    # Detect cycles reachable from root.
    visiting: set[str] = set()
    visited: set[str] = set()
    def dfs(node: str):
        if node in visiting:
            problems.append(f"cycle detected at element {node!r}")
            return
        if node in visited or node not in elements:
            return
        visiting.add(node)
        for child in elements[node].get("children", []):
            dfs(child)
        visiting.remove(node)
        visited.add(node)
    if isinstance(root, str):
        dfs(root)

    for path, text in iter_strings(spec):
        if EXTERNAL_RE.search(text):
            problems.append(f"external URL-like value blocked at {path}")
        if SECRET_RE.search(text):
            problems.append(f"credential-like value blocked at {path}")
        if ACCOUNT_ID_RE.search(text) and not allow_account_ids:
            problems.append(f"12-digit account-like value blocked at {path}; use unknown / needs refresh or --allow-account-ids")
        if RAW_HTML_RE.search(text):
            problems.append(f"raw HTML/SVG-like value blocked at {path}; use catalog components instead")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--catalog", default=None)
    parser.add_argument("--allow-account-ids", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    catalog_path = Path(args.catalog).expanduser() if args.catalog else skill_dir / "references" / "component-catalog.json"
    spec = load_json(Path(args.spec).expanduser())
    catalog = load_json(catalog_path)
    problems = validate(spec, catalog, args.allow_account_ids)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 2
    print("OK: spec validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
