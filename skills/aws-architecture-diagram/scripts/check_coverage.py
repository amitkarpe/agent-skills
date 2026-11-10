#!/usr/bin/env python3
"""Prove a diagram spec accounts for every discovered resource.

PASS only when:
  - every discovery key is in exactly one node `covers` list or in
    `coverage.omitted` with a non-empty reason;
  - no `covers` or `omitted` key is missing from the discovery (nothing invented);
  - `coverage.discovery_sha256` matches the discovery file (the spec is not stale).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("discovery", type=Path)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args()


def check(discovery_bytes: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    discovery = json.loads(discovery_bytes)
    errors: list[str] = []
    found = {r["key"] for r in discovery.get("resources", [])}
    coverage = spec.get("coverage")
    if not isinstance(coverage, dict):
        return {"status": "FAIL", "errors": ["spec has no coverage block"], "resources": len(found)}

    expected_sha = coverage.get("discovery_sha256")
    actual_sha = hashlib.sha256(discovery_bytes).hexdigest()
    if expected_sha != actual_sha:
        errors.append("coverage.discovery_sha256 does not match the discovery file; re-run discovery_to_spec or update the spec")

    covered: Counter[str] = Counter()
    for node in spec.get("nodes", []):
        for key in node.get("covers", []) or []:
            covered[key] += 1
    omitted: Counter[str] = Counter()
    for item in coverage.get("omitted", []) or []:
        key = item.get("key")
        omitted[key] += 1
        if not str(item.get("reason", "")).strip():
            errors.append(f"omitted resource has no reason: {key}")

    for key, count in covered.items():
        if count > 1:
            errors.append(f"resource drawn by {count} nodes: {key}")
    for key, count in omitted.items():
        if count > 1:
            errors.append(f"resource omitted {count} times: {key}")
    for key in sorted(set(covered) & set(omitted)):
        errors.append(f"resource both drawn and omitted: {key}")
    for key in sorted((set(covered) | set(omitted)) - found):
        errors.append(f"resource not in discovery (invented or stale): {key}")
    missing = sorted(found - set(covered) - set(omitted))
    for key in missing:
        errors.append(f"discovered resource not accounted for: {key}")

    return {
        "status": "FAIL" if errors else "PASS",
        "resources": len(found),
        "drawn": len(set(covered) & found),
        "omitted": len(set(omitted) & found),
        "missing": len(missing),
        "discovery_sha256": actual_sha,
        "errors": errors,
    }


def main() -> None:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    report = check(args.discovery.read_bytes(), spec)
    if args.output_json:
        args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for error in report["errors"][:50]:
        print(f"ERROR {error}", file=sys.stderr)
    if len(report["errors"]) > 50:
        print(f"ERROR ... {len(report['errors']) - 50} more", file=sys.stderr)
    print(
        f"{report['status']} coverage resources={report['resources']} drawn={report.get('drawn', 0)} "
        f"omitted={report.get('omitted', 0)} missing={report.get('missing', 0)}"
    )
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
