#!/usr/bin/env python3
"""Deterministic, local-only Synapxe VA report review."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import email
import hashlib
import html
import json
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN")
REQUIRED_COLUMNS = ("app", "severity", "ip", "finding")
COLUMN_ALIASES = {
    "app": ("AppSystem", "Application", "Application System", "App System"),
    "severity": ("Severity", "Risk", "Risk Rating"),
    "ip": ("IP", "IP Address", "IP_Address", "Host IP", "Asset IP"),
    "finding": ("Plugin Name", "Finding", "Name", "Vulnerability", "Plugin ID"),
    "hostname": ("Hostname", "Host Name", "DNS Name", "FQDN"),
    "action": ("Action", "Recommended Action", "Disposition", "Status"),
    "scan_date": ("Scan Date", "Observation Date", "Last Observed", "Last Scan", "AuthenticatedScanTime"),
}


class ReviewError(RuntimeError):
    pass


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_filename(name: str, fallback: str) -> str:
    candidate = Path(name or fallback).name
    candidate = re.sub(r"[^A-Za-z0-9._ -]", "_", candidate).strip(" .")
    return candidate or fallback


def ensure_output_path(source: Path, output: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    if output in (Path("/"), Path.home()) or output == source or output in source.parents:
        raise ReviewError(f"unsafe output path: {output}")
    if source in output.parents:
        raise ReviewError(f"output path must not contain the source: {output}")


def col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref)
    if not letters:
        raise ReviewError(f"invalid XLSX cell reference: {ref}")
    value = 0
    for letter in letters.group(0):
        value = value * 26 + ord(letter) - 64
    return value - 1


def xlsx_rows(path: Path) -> dict[str, list[list[str]]]:
    namespace = {"m": MAIN_NS, "r": REL_NS}
    rel_namespace = {"p": PKG_REL_NS}
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ReviewError(f"corrupt XLSX input: {path.name}") from exc
    with archive:
        required = {"xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
        if not required.issubset(set(archive.namelist())):
            raise ReviewError(f"unsupported XLSX schema: missing workbook metadata in {path.name}")
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(item.itertext()) for item in root.findall("m:si", namespace)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib.get("Id"): item.attrib.get("Target", "") for item in rels.findall("p:Relationship", rel_namespace)}
        result: dict[str, list[list[str]]] = {}
        for sheet in workbook.findall("m:sheets/m:sheet", namespace):
            name = text(sheet.attrib.get("name"))
            rel_id = sheet.attrib.get(f"{{{REL_NS}}}id")
            target = targets.get(rel_id, "").lstrip("/")
            sheet_path = target if target.startswith("xl/") else f"xl/{target}"
            if not name or not target or sheet_path not in archive.namelist():
                raise ReviewError(f"unsupported XLSX schema: unresolved worksheet {name or '<unnamed>'}")
            root = ET.fromstring(archive.read(sheet_path))
            parsed: list[list[str]] = []
            for row in root.findall("m:sheetData/m:row", namespace):
                cells: dict[int, str] = {}
                for cell in row.findall("m:c", namespace):
                    index = col_index(cell.attrib.get("r", ""))
                    value = cell.find("m:v", namespace)
                    inline = cell.find("m:is", namespace)
                    raw = "" if value is None else text(value.text)
                    if cell.attrib.get("t") == "s" and raw:
                        raw = shared[int(raw)]
                    elif cell.attrib.get("t") == "inlineStr" and inline is not None:
                        raw = "".join(inline.itertext())
                    cells[index] = raw
                width = max(cells, default=-1) + 1
                parsed.append([cells.get(index, "") for index in range(width)])
            result[name] = parsed
        return result


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def html_rows(path: Path) -> dict[str, list[list[str]]]:
    parser = TableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return {f"table-{index + 1}": table for index, table in enumerate(parser.tables)}


def extract_eml(source: Path, destination: Path) -> tuple[dict[str, Any], list[Path]]:
    try:
        message = BytesParser(policy=policy.default).parsebytes(source.read_bytes())
    except Exception as exc:  # email parser errors are input failures
        raise ReviewError(f"corrupt EML input: {source.name}") from exc
    attachments: list[dict[str, Any]] = []
    candidates: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    for index, part in enumerate(message.walk()):
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        if not filename or payload is None:
            continue
        safe = safe_filename(filename, f"attachment-{index}")
        stem, suffix = Path(safe).stem, Path(safe).suffix
        counter = 2
        while safe.lower() in used:
            safe = f"{stem}-{counter}{suffix}"
            counter += 1
        used.add(safe.lower())
        path = destination / safe
        path.write_bytes(payload)
        content_type = part.get_content_type()
        attachments.append({"filename": safe, "content_type": content_type, "bytes": len(payload), "sha256": sha256(path)})
        if path.suffix.lower() in (".xlsx", ".html", ".htm"):
            candidates.append(path)
    metadata = {
        "subject": text(message.get("Subject")),
        "date": text(message.get("Date")),
        "from": text(message.get("From")),
        "to": text(message.get("To")),
        "attachments": attachments,
    }
    (destination / "email-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not candidates:
        raise ReviewError("EML has no supported XLSX or HTML attachment")
    candidates.sort(key=lambda item: (0 if item.suffix.lower() == ".xlsx" else 1, item.name.lower()))
    return metadata, candidates


def map_headers(rows: list[list[str]]) -> tuple[int, dict[str, int], list[str]]:
    for row_number, row in enumerate(rows[:25]):
        normalized = {text(value).casefold(): index for index, value in enumerate(row) if text(value)}
        mapped: dict[str, int] = {}
        for canonical, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias.casefold() in normalized:
                    mapped[canonical] = normalized[alias.casefold()]
                    break
        if all(field in mapped for field in REQUIRED_COLUMNS):
            return row_number, mapped, [text(value) for value in row]
    raise ReviewError("unsupported workbook schema: required AppSystem, Severity, IP, and finding columns were not found")


def choose_table(tables: dict[str, list[list[str]]], requested_sheet: str | None = None) -> tuple[str, int, dict[str, int], list[str], list[str]]:
    matches: list[tuple[str, int, dict[str, int], list[str]]] = []
    warnings: list[str] = []
    for name in sorted(tables):
        try:
            header_row, mapping, headers = map_headers(tables[name])
            matches.append((name, header_row, mapping, headers))
        except ReviewError as exc:
            warnings.append(f"{name}: {exc}")
    if not matches:
        raise ReviewError("unsupported workbook schema; " + "; ".join(warnings))
    if requested_sheet:
        for match in matches:
            if match[0] == requested_sheet:
                return (*match, warnings)
        available = ", ".join(match[0] for match in matches)
        raise ReviewError(f"requested worksheet {requested_sheet!r} does not have the required schema; matching worksheets: {available}")
    if len(matches) > 1:
        for match in matches:
            if match[0] == "MasterVA":
                warnings.append("multiple matching worksheets detected; selected canonical worksheet MasterVA. Use --sheet to override explicitly.")
                return (*match, warnings)
        available = ", ".join(match[0] for match in matches)
        raise ReviewError(f"unsupported workbook schema: multiple tables match required columns ({available}); use --sheet")
    return (*matches[0], warnings)


def severity(raw: str) -> str:
    value = text(raw).upper()
    if "CRIT" in value or value in {"4", "5"}:
        return "CRITICAL"
    if "HIGH" in value or value in {"3", "2 - HIGH"}:
        return "HIGH"
    if "MED" in value or value in {"2", "3 - MEDIUM"}:
        return "MEDIUM"
    if "LOW" in value or value in {"1", "4 - LOW"}:
        return "LOW"
    if "INFO" in value:
        return "INFO"
    return "UNKNOWN"


def value_at(row: list[str], index: int | None) -> str:
    return text(row[index]) if index is not None and index < len(row) else ""


def normalize_rows(table: list[list[str]], header_row: int, mapping: dict[str, int], app_system: str) -> tuple[list[dict[str, str]], int]:
    normalized: list[dict[str, str]] = []
    skipped_blank = 0
    for row_number, row in enumerate(table[header_row + 1 :], start=header_row + 2):
        app = value_at(row, mapping["app"])
        if not any(text(item) for item in row):
            skipped_blank += 1
            continue
        if app != app_system:
            continue
        normalized.append({
            "source_row": str(row_number),
            "app_system": app,
            "severity": severity(value_at(row, mapping["severity"])),
            "severity_raw": value_at(row, mapping["severity"]),
            "ip": value_at(row, mapping["ip"]),
            "finding": value_at(row, mapping["finding"]),
            "hostname": value_at(row, mapping.get("hostname")),
            "action": value_at(row, mapping.get("action")) or "unknown",
            "scan_date": value_at(row, mapping.get("scan_date")) or "unknown",
        })
    if not normalized:
        raise ReviewError(f"no matching rows for exact AppSystem == {app_system!r}")
    return normalized, skipped_blank


def load_inventory(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    if not path.is_file():
        raise ReviewError(f"inventory mapping file is missing: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t" if path.suffix.lower() == ".tsv" else ","))
    if not rows or not rows[0]:
        raise ReviewError("inventory mapping has no headers")
    lower = {name.casefold(): name for name in rows[0]}
    ip_key = lower.get("ip") or lower.get("ip address")
    if not ip_key:
        raise ReviewError("inventory mapping requires an IP column")
    mapping: dict[str, dict[str, str]] = {}
    for row in rows:
        ip = text(row.get(ip_key))
        if ip:
            mapping[ip] = {text(key): text(value) for key, value in row.items() if text(key)}
    return mapping


def comparison_text(value: Any) -> str:
    return " ".join(text(value).split())


def comparison_key(ip: Any, finding: Any, severity_value: Any) -> str:
    return "|".join((comparison_text(ip), comparison_text(finding), severity(severity_value)))


def row_value(row: dict[str, Any], aliases: tuple[str, ...]) -> str:
    available = {text(key).casefold(): key for key in row if text(key)}
    for alias in aliases:
        key = available.get(alias.casefold())
        if key is not None:
            return text(row.get(key))
    return ""


def prior_keys(path: Path | None) -> tuple[set[str], str]:
    if path is None:
        return set(), ""
    if not path.is_file():
        raise ReviewError(f"prior normalized result is missing: {path}")
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("rows", data) if isinstance(data, dict) else data
    else:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t" if path.suffix.lower() == ".tsv" else ","))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ReviewError("prior normalized result must contain row objects")
    keys = set()
    for row in rows:
        ip = row_value(row, ("ip", "IP", "IP Address", "IP_Address"))
        finding = row_value(row, ("finding", "Name", "Plugin Name", "Plugin ID", "Vulnerability"))
        severity_value = row_value(row, ("severity", "Severity", "Risk", "Risk Rating"))
        if not ip or not finding or not severity_value:
            raise ReviewError("prior normalized result is incompatible: requires IP, finding/Name, and Severity columns")
        keys.add(comparison_key(ip, finding, severity_value))
    return keys, "ip|finding|normalized_severity"


def record_key(row: dict[str, str]) -> str:
    return comparison_key(row["ip"], row["finding"], row["severity"])


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ("source_row", "app_system", "severity", "severity_raw", "ip", "finding", "hostname", "action", "scan_date", "inventory_mapping")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def html_report(summary: dict[str, Any], rows: list[dict[str, str]]) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    severity_cards = "".join(f"<article><b>{esc(name.title())}</b><strong>{summary['severity'].get(name, 0)}</strong></article>" for name in SEVERITY_ORDER[:4])
    comparison = summary["comparison"]
    comparison_cards = "" if not comparison["compatible"] else "".join(
        f"<article><b>{esc(label)}</b><strong>{comparison[key]}</strong></article>"
        for key, label in (("recurring", "Recurring"), ("new_or_changed", "New or changed"), ("prior_only", "Prior only"))
    )
    host_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        host_groups[row["ip"] or "unknown IP"].append(row)
    host_rows = []
    for ip, grouped in sorted(host_groups.items(), key=lambda item: (
        -sum(row["severity"] == "CRITICAL" for row in item[1]),
        -sum(row["severity"] == "HIGH" for row in item[1]),
        -len(item[1]), item[0],
    )):
        counts = Counter(item["severity"] for item in grouped)
        hosts = sorted({item["hostname"] for item in grouped if item["hostname"]}) or ["unknown"]
        mapping = sorted({item["inventory_mapping"] for item in grouped if item["inventory_mapping"]}) or ["unknown"]
        host_rows.append(
            f"<tr><td>{esc(ip)}</td><td>{esc(', '.join(hosts))}</td><td>{len(grouped)}</td>"
            f"<td>{counts['CRITICAL']}</td><td>{counts['HIGH']}</td><td>{counts['MEDIUM']}</td><td>{counts['LOW']}</td>"
            f"<td>{esc(', '.join(mapping))}</td></tr>"
        )
    findings: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["severity"] in ("CRITICAL", "HIGH"):
            findings[(row["severity"], row["finding"])].append(row)
    finding_rows = []
    ranked_findings = sorted(
        findings.items(),
        key=lambda item: (SEVERITY_ORDER.index(item[0][0]), -len({row["ip"] or "unknown" for row in item[1]}), -len(item[1]), item[0][1]),
    )[:5]
    for (sev, finding), grouped in ranked_findings:
        ips = sorted({item["ip"] or "unknown" for item in grouped})
        actions = sorted({item["action"] for item in grouped})
        finding_rows.append(
            f"<tr><td>{esc(sev.title())}</td><td>{esc(finding)}</td><td>{len(grouped)}</td>"
            f"<td>{len(ips)}<details><summary>Show affected IPs</summary><code>{esc(', '.join(ips))}</code></details></td>"
            f"<td>{esc(', '.join(actions))}</td></tr>"
        )
    high_risk_rows = sum(summary["severity"][name] for name in ("CRITICAL", "HIGH"))
    high_risk_ips = len({row["ip"] for row in rows if row["ip"] and row["severity"] in ("CRITICAL", "HIGH")})
    comparison_fact = (
        f"Prior evidence: {comparison['recurring']} recurring, {comparison['new_or_changed']} new or changed, {comparison['prior_only']} prior only."
        if comparison["compatible"] else "Prior comparison: not supplied."
    )
    coverage = summary["mapping_coverage"]
    facts = (
        f"Critical + High: {high_risk_rows} report rows across {high_risk_ips} affected IPs.",
        comparison_fact,
        f"Workbook actions: Remediation {summary['actions'].get('Remediation', 0)}, Recast {summary['actions'].get('Recast', 0)}.",
        f"Workbook hostnames: {coverage['workbook_hostname_ips']} of {summary['unique_ips']} unique IPs.",
        f"Local inventory mappings: {coverage['inventory_mapped_ips']} of {summary['unique_ips']} unique IPs.",
    )
    warnings = "".join(f"<li>{esc(item)}</li>" for item in summary["warnings"]) or "<li>none</li>"
    return f"""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{esc(summary['app_system'])} VA review</title><style>:root{{--bg:#07111f;--panel:#10233a;--line:#31506d;--text:#eef6ff;--muted:#afc1d4}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:32px 20px 56px}}h1,h2{{line-height:1.15}}.muted{{color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}}article,.box{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}}article b{{display:block;color:var(--muted);font-size:14px}}article strong{{font-size:30px}}.facts{{padding-left:24px}}.facts li{{margin:7px 0}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:12px}}table{{width:100%;min-width:720px;border-collapse:collapse;background:var(--panel)}}th,td{{padding:9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{color:var(--muted);font-size:13px}}details{{margin-top:4px}}summary{{cursor:pointer;color:var(--muted)}}code{{word-break:break-all}}@media(max-width:720px){{main{{padding:20px 12px}}.cards{{grid-template-columns:repeat(2,1fr)}}table{{font-size:13px}}}}</style></head><body><main><p class=\"muted\">Local evidence-only VA review</p><h1>{esc(summary['app_system'])}</h1><p>Report date: <b>{esc(summary['report_date'])}</b> · Scan/observation dates: <b>{esc(', '.join(summary['scan_dates']) or 'unknown')}</b> · Evidence cutoff: <b>{esc(summary['evidence_cutoff'])}</b></p><h2>Executive snapshot</h2><section class=\"cards\"><article><b>Filtered rows</b><strong>{summary['row_count']}</strong></article><article><b>Unique IPs</b><strong>{summary['unique_ips']}</strong></article>{severity_cards}<article><b>Remediation</b><strong>{summary['actions'].get('Remediation', 0)}</strong></article><article><b>Recast</b><strong>{summary['actions'].get('Recast', 0)}</strong></article>{comparison_cards}</section><h2>Operator facts</h2><ol class=\"facts\">{''.join(f'<li>{esc(fact)}</li>' for fact in facts)}</ol><h2>Interpretation boundary</h2><div class=\"box\">Prior comparison is key-based evidence against the supplied prior using <code>{esc(comparison.get('key') or 'not supplied')}</code>; it is not remediation, exposure, current-state, or false-positive proof. Workbook action labels are source classifications only.</div><h2>Top five Critical/High findings</h2><div class=\"table-wrap\"><table><thead><tr><th>Severity</th><th>Finding</th><th>Rows</th><th>Affected IPs</th><th>Workbook action</th></tr></thead><tbody>{''.join(finding_rows) or '<tr><td colspan=5>none</td></tr>'}</tbody></table></div><h2>Host priority</h2><div class=\"table-wrap\"><table><thead><tr><th>IP</th><th>Workbook host</th><th>Total</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Local inventory mapping</th></tr></thead><tbody>{''.join(host_rows)}</tbody></table></div><h2>Mapping coverage</h2><div class=\"box\">Workbook hostnames: <b>{coverage['workbook_hostname_ips']}</b> of <b>{summary['unique_ips']}</b> unique IPs. Local inventory mappings: <b>{coverage['inventory_mapped_ips']}</b> of <b>{summary['unique_ips']}</b> unique IPs. Unidentified by workbook or local inventory: <b>{coverage['unmapped_ips']}</b> unique IPs.</div><h2>Integrity and warnings</h2><ul><li>Source SHA256: <code>{esc(summary['source_sha256'])}</code></li><li>Parser table: {esc(summary['table'])}; header row: {summary['header_row']}</li><li>Duplicate records observed: {summary['duplicate_records']}; source rows remain preserved.</li>{warnings}</ul></main></body></html>"""


def manifest(root: Path) -> None:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "MANIFEST.tsv"):
        rows.append((str(path.relative_to(root)), sha256(path)))
    with (root / "MANIFEST.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("path", "sha256"))
        writer.writerows(rows)


def review(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output_dir).expanduser().resolve()
    if not source.is_file():
        raise ReviewError(f"input file is missing: {source}")
    ensure_output_path(source, output)
    if output.exists():
        raise ReviewError(f"output directory already exists: {output}")
    output.mkdir(parents=True)
    copied_source = output / "source" / safe_filename(source.name, "source")
    copied_source.parent.mkdir()
    shutil.copy2(source, copied_source)
    attachments: list[Path] = []
    report_date = args.report_date or "unknown"
    input_path = source
    if source.suffix.lower() == ".eml":
        metadata, attachments = extract_eml(source, output / "attachments")
        input_path = attachments[0]
        report_date = args.report_date or metadata["date"] or "unknown"
    if input_path.suffix.lower() == ".xlsx":
        tables = xlsx_rows(input_path)
    elif input_path.suffix.lower() in (".html", ".htm"):
        tables = html_rows(input_path)
    else:
        raise ReviewError(f"unsupported input type: {input_path.suffix or '<none>'}")
    table_name, header_row, mapping, headers, schema_warnings = choose_table(tables, args.sheet)
    rows, skipped_blank = normalize_rows(tables[table_name], header_row, mapping, args.app_system)
    inventory = load_inventory(Path(args.inventory).expanduser().resolve() if args.inventory else None)
    for row in rows:
        local = inventory.get(row["ip"])
        row["inventory_mapping"] = json.dumps(local, sort_keys=True) if local else "unknown"
    counts = Counter(row["severity"] for row in rows)
    unique_ips = {row["ip"] for row in rows if row["ip"]}
    duplicate_records = sum(value - 1 for value in Counter(record_key(row) for row in rows).values() if value > 1)
    scan_dates = sorted({row["scan_date"] for row in rows if row["scan_date"] != "unknown"})
    actions = Counter(row["action"] for row in rows)
    workbook_hostname_ips = {row["ip"] for row in rows if row["ip"] and row["hostname"]}
    inventory_mapped_ips = {row["ip"] for row in rows if row["ip"] and row["inventory_mapping"] != "unknown"}
    prior, comparison_key_name = prior_keys(Path(args.prior).expanduser().resolve() if args.prior else None)
    current = {record_key(row) for row in rows}
    warnings = list(schema_warnings)
    if duplicate_records:
        warnings.append(f"{duplicate_records} duplicate record(s) observed; report rows were preserved for reconciliation.")
    if len(scan_dates) > 1:
        warnings.append("mixed scan/observation dates; report period is not current-state proof.")
    if not inventory:
        warnings.append("no local inventory mapping supplied; host mappings remain unknown unless present in the workbook.")
    summary: dict[str, Any] = {
        "app_system": args.app_system,
        "source": source.name,
        "source_sha256": sha256(source),
        "selected_attachment": input_path.name if attachments else None,
        "attachment_count": len(attachments),
        "table": table_name,
        "header_row": header_row + 1,
        "headers": headers,
        "row_count": len(rows),
        "unique_ips": len(unique_ips),
        "severity": {name: counts.get(name, 0) for name in SEVERITY_ORDER},
        "actions": dict(sorted(actions.items())),
        "scan_dates": scan_dates,
        "report_date": report_date,
        "evidence_cutoff": args.evidence_cutoff or "not supplied",
        "duplicate_records": duplicate_records,
        "unknown_inventory_mappings": sum(1 for row in rows if row["inventory_mapping"] == "unknown"),
        "mapping_coverage": {
            "workbook_hostname_ips": len(workbook_hostname_ips),
            "inventory_mapped_ips": len(inventory_mapped_ips),
            "unmapped_ips": len(unique_ips - workbook_hostname_ips - inventory_mapped_ips),
        },
        "skipped_blank_rows": skipped_blank,
        "comparison": {"compatible": bool(args.prior), "key": comparison_key_name, "recurring": len(current & prior), "new_or_changed": len(current - prior), "prior_only": len(prior - current)} if args.prior else {"compatible": False},
        "warnings": warnings,
    }
    write_tsv(output / "normalized_rows.tsv", rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "output.html").write_text(html_report(summary, rows), encoding="utf-8")
    result = ["# VA report review result", "", "result: complete", f"rows: {summary['row_count']}", f"unique_ips: {summary['unique_ips']}", f"severity: " + ", ".join(f"{key}={summary['severity'][key]}" for key in SEVERITY_ORDER[:4]), f"source_sha256: {summary['source_sha256']}", f"warnings: {len(warnings)}", "public_exposure: none", ""]
    (output / "RESULT.md").write_text("\n".join(result), encoding="utf-8")
    manifest(output)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="EML, XLSX, or HTML report path")
    parser.add_argument("--output-dir", required=True, help="new output directory")
    parser.add_argument("--app-system", default="Lifebit-Synapxe")
    parser.add_argument("--prior", help="optional normalized TSV/CSV/JSON result")
    parser.add_argument("--inventory", help="optional local CSV/TSV inventory mapping")
    parser.add_argument("--sheet", help="explicit worksheet/table name when schema is ambiguous")
    parser.add_argument("--report-date")
    parser.add_argument("--evidence-cutoff")
    args = parser.parse_args()
    try:
        summary = review(args)
    except (ReviewError, OSError, ValueError, ET.ParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
