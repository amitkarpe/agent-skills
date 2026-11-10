#!/usr/bin/env python3
"""Normalize read-only discovery output into one discovery.json resource list.

Inputs (repeat --input for each account or stack):
  config     output of `aws configservice select-resource-config` (or the
             aggregate form), one JSON object or a JSON list of pages
  terraform  output of `terraform show -json`

The result is evidence, not a diagram. It may hold resource IDs, so keep it
outside Git (for example under ~/.AGENTS-temp/<repo>/).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input",
        nargs=3,
        action="append",
        required=True,
        metavar=("KIND", "GROUP", "PATH"),
        help="KIND is config or terraform; GROUP is a short display label such as DEV or PROD",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--collected-at", help="ISO time the discovery ran (default: now, UTC)")
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_items(document: Any) -> Iterator[dict[str, Any]]:
    pages = document if isinstance(document, list) else [document]
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("config input must be a JSON object or a list of objects")
        for raw in page.get("Results", []):
            item = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(item, dict):
                yield item


def tag_value(tags: Any, name: str) -> str | None:
    if isinstance(tags, dict):
        value = tags.get(name)
        return str(value) if value else None
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and tag.get("key", tag.get("Key")) == name:
                value = tag.get("value", tag.get("Value"))
                return str(value) if value else None
    return None


def from_config(group: str, document: Any) -> list[dict[str, Any]]:
    resources = []
    for item in config_items(document):
        rtype = str(item.get("resourceType", ""))
        rid = str(item.get("resourceId", ""))
        if not rtype or not rid:
            continue
        name = tag_value(item.get("tags"), "Name") or item.get("resourceName") or rid
        relations = []
        for rel in item.get("relationships") or []:
            if not isinstance(rel, dict) or not rel.get("resourceId") or not rel.get("resourceType"):
                continue
            relations.append(
                {
                    "to": f"{group}/{rel['resourceType']}/{rel['resourceId']}",
                    "name": str(rel.get("relationshipName", "related to")),
                }
            )
        resources.append(
            {
                "key": f"{group}/{rtype}/{rid}",
                "kind": "config",
                "group": group,
                "type": rtype,
                "name": str(name),
                "relations": relations,
            }
        )
    return resources


def walk_modules(module: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield from module.get("resources", []) or []
    for child in module.get("child_modules", []) or []:
        yield from walk_modules(child)


def from_terraform(group: str, document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise ValueError("terraform input must be the JSON object from `terraform show -json`")
    root = (document.get("values") or {}).get("root_module") or {}
    resources = []
    for item in walk_modules(root):
        if item.get("mode") != "managed":
            continue  # data sources are lookups, not deployed resources
        address = str(item.get("address", ""))
        values = item.get("values") or {}
        name = tag_value(values.get("tags"), "Name") or values.get("name") or item.get("name") or address
        relations = [
            {"to": f"{group}/{dep}", "name": "depends on"}
            for dep in item.get("depends_on", []) or []
            if not str(dep).startswith("data.")
        ]
        resources.append(
            {
                "key": f"{group}/{address}",
                "kind": "terraform",
                "group": group,
                "type": str(item.get("type", "")),
                "name": str(name),
                "relations": relations,
            }
        )
    return resources


def main() -> None:
    args = parse_args()
    resources: list[dict[str, Any]] = []
    sources = []
    for kind, group, raw_path in args.input:
        path = Path(raw_path).expanduser()
        document = json.loads(path.read_text(encoding="utf-8"))
        if kind == "config":
            found = from_config(group, document)
        elif kind == "terraform":
            found = from_terraform(group, document)
        else:
            raise SystemExit(f"FAIL unknown input kind: {kind} (use config or terraform)")
        sources.append({"kind": kind, "group": group, "file": path.name, "sha256": sha256(path), "resources": len(found)})
        resources.extend(found)

    seen: dict[str, dict[str, Any]] = {}
    for resource in resources:
        if resource["key"] in seen:
            raise SystemExit(f"FAIL duplicate resource key across inputs: {resource['key']}")
        seen[resource["key"]] = resource

    collected = args.collected_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    output = {
        "schema_version": 1,
        "collected_at": collected,
        "sources": sources,
        "resources": sorted(resources, key=lambda item: item["key"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS discovery resources={len(resources)} sources={len(sources)} output={args.output}")


if __name__ == "__main__":
    main()
