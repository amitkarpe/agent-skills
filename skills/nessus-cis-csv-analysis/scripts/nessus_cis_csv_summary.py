#!/usr/bin/env python3
import argparse
import collections
import csv
import json
import re
from pathlib import Path


REQUIRED = {"Plugin", "Plugin Name", "Severity", "IP Address", "DNS Name", "Plugin Output"}


def result_from_output(output: str) -> str:
    match = re.search(r"Result:\s*([A-Z]+)", output or "")
    if match:
        return match.group(1)
    if "was found to be open" in (output or ""):
        return "PORT"
    return "NO_RESULT"


def compact_output(output: str, limit: int = 900) -> str:
    text = " ".join((output or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def category(name: str) -> str:
    lower = name.lower()
    if "audit" in lower:
        return "audit"
    if "log" in lower or "journald" in lower or "rsyslog" in lower:
        return "logging"
    if "selinux" in lower or "unconfined" in lower:
        return "selinux"
    if "banner" in lower or "message of the day" in lower:
        return "banner"
    if "cron" in lower:
        return "scheduler"
    if "password" in lower or "authselect" in lower or "su command" in lower:
        return "auth"
    if "usb" in lower or "filesystem" in lower or "file permissions" in lower or "unowned" in lower:
        return "filesystem"
    if "chrony" in lower or "time" in lower:
        return "time"
    if "ip forwarding" in lower or "ipv6" in lower or "listening" in lower:
        return "network"
    if "gpg" in lower or "repo" in lower or "package" in lower:
        return "package-trust"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    with csv_path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rows = list(csv.DictReader(fh))

    if not rows:
        raise SystemExit("CSV is empty")
    missing = REQUIRED - set(rows[0].keys())
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    severity_counts = collections.Counter()
    result_counts = collections.Counter()
    by_severity_result = collections.defaultdict(collections.Counter)
    host_ips = collections.Counter()
    host_dns = collections.Counter()
    categories = collections.defaultdict(collections.Counter)
    findings = []

    for row in rows:
        severity = row["Severity"] or "Unknown"
        result = result_from_output(row.get("Plugin Output", ""))
        name = row["Plugin Name"]
        cat = category(name)
        severity_counts[severity] += 1
        result_counts[result] += 1
        by_severity_result[severity][result] += 1
        categories[severity][cat] += 1
        host_ips[row["IP Address"]] += 1
        host_dns[row["DNS Name"]] += 1
        findings.append(
            {
                "plugin": row["Plugin"],
                "name": name,
                "severity": severity,
                "result": result,
                "category": cat,
                "ip": row["IP Address"],
                "dns": row["DNS Name"],
                "first_discovered": row.get("First Discovered", ""),
                "last_observed": row.get("Last Observed", ""),
                "output": compact_output(row.get("Plugin Output", "")),
            }
        )

    summary = {
        "source": str(csv_path),
        "total_rows": len(rows),
        "control_rows": len([f for f in findings if f["result"] not in ("PORT", "NO_RESULT")]),
        "inventory_rows": len([f for f in findings if f["result"] in ("PORT", "NO_RESULT")]),
        "host_ips": dict(host_ips),
        "host_dns": dict(host_dns),
        "severity_counts": dict(severity_counts),
        "result_counts": dict(result_counts),
        "by_severity_result": {k: dict(v) for k, v in by_severity_result.items()},
        "categories": {k: dict(v) for k, v in categories.items()},
        "open_high": [f for f in findings if f["severity"] == "High"],
        "open_medium": [f for f in findings if f["severity"] == "Medium"],
        "passed_info": [f for f in findings if f["severity"] == "Info" and f["result"] == "PASSED"],
        "inventory_info": [f for f in findings if f["severity"] == "Info" and f["result"] != "PASSED"],
    }

    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
