#!/usr/bin/env python3
import csv
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from email.message import EmailMessage
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review_va_report.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
HEADERS = ["AppSystem", "Severity", "IP Address", "Plugin Name", "Hostname", "Action", "Scan Date"]


def column_name(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def worksheet(rows):
    values = []
    for row_number, row in enumerate(rows, start=1):
        cells = []
        for index, value in enumerate(row, start=1):
            cells.append(f'<c r="{column_name(index)}{row_number}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        values.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    return f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(values)}</sheetData></worksheet>'


def write_xlsx(path, rows, sheet="MasterVA"):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", """<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>""")
        archive.writestr("_rels/.rels", """<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>""")
        archive.writestr("xl/workbook.xml", f'''<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{escape(sheet)}" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        archive.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>""")
        archive.writestr("xl/worksheets/sheet1.xml", worksheet(rows))


def run_report(source, output, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), str(source), "--output-dir", str(output), *extra], text=True, capture_output=True)


class VAReviewTests(unittest.TestCase):
    def fixture_rows(self):
        return [HEADERS,
            ["Lifebit-Synapxe", "Critical", "10.0.0.1", "<script>alert(1)</script>", "host-a", "Remediation", "2026-07-05"],
            ["Lifebit-Synapxe", "2 - High", "10.0.0.2", "Finding B", "", "Recast", "2026-07-19"],
            ["Healix", "Critical", "10.0.0.3", "Ignore", "healix", "Remediation", "2026-07-05"],
            ["Other", "Low", "10.0.0.4", "Ignore", "other", "Remediation", "2026-07-05"],
        ]

    def test_eml_filter_escape_dates_mapping_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); xlsx = base / "source.xlsx"; eml = base / "source.eml"; output = base / "out"; inventory = base / "inventory.tsv"
            write_xlsx(xlsx, self.fixture_rows())
            msg = EmailMessage(); msg["Subject"] = "Synthetic VA"; msg["Date"] = "Mon, 20 Jul 2026 08:00:00 +0800"; msg.set_content("test"); msg.add_attachment(xlsx.read_bytes(), maintype="application", subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="fixture.xlsx"); eml.write_bytes(msg.as_bytes())
            inventory.write_text("ip\tinstance\n10.0.0.1\ti-test\n")
            result = run_report(eml, output, "--evidence-cutoff", "2026-07-21", "--inventory", str(inventory))
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["row_count"], 2); self.assertEqual(summary["unique_ips"], 2)
            self.assertEqual(summary["severity"]["CRITICAL"], 1); self.assertEqual(summary["severity"]["HIGH"], 1)
            self.assertEqual(summary["scan_dates"], ["2026-07-05", "2026-07-19"])
            report = (output / "output.html").read_text()
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", report); self.assertNotIn("<script>alert(1)</script>", report)
            self.assertTrue((output / "attachments" / "fixture.xlsx").is_file()); self.assertTrue((output / "MANIFEST.tsv").is_file())

    def test_duplicate_records_are_preserved_and_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base / "dupe.xlsx"; output = base / "out"
            rows = [HEADERS, ["Lifebit-Synapxe", "High", "10.0.0.1", "Same", "", "Remediation", "2026-07-05"], ["Lifebit-Synapxe", "High", "10.0.0.1", "Same", "", "Remediation", "2026-07-05"]]
            write_xlsx(source, rows)
            result = run_report(source, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["row_count"], 2); self.assertEqual(summary["duplicate_records"], 1)

    def test_missing_columns_corrupt_input_and_no_match_fail_clearly(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            bad_schema = base / "bad.xlsx"; write_xlsx(bad_schema, [["AppSystem", "Severity"], ["Lifebit-Synapxe", "High"]])
            self.assertIn("unsupported workbook schema", run_report(bad_schema, base / "schema-out").stderr)
            corrupt = base / "corrupt.xlsx"; corrupt.write_text("not an xlsx")
            self.assertIn("corrupt XLSX", run_report(corrupt, base / "corrupt-out").stderr)
            no_match = base / "nomatch.xlsx"; write_xlsx(no_match, [HEADERS, ["Healix", "High", "10.0.0.1", "x", "", "Remediation", "2026-07-05"]])
            self.assertIn("no matching rows", run_report(no_match, base / "nomatch-out").stderr)

    def test_html_and_prior_comparison(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base / "report.html"; output = base / "out"; prior = base / "prior.tsv"
            source.write_text("<table><tr>" + "".join(f"<th>{item}</th>" for item in HEADERS) + "</tr><tr><td>Lifebit-Synapxe</td><td>medium</td><td>10.0.0.5</td><td>A</td><td></td><td>Remediation</td><td>2026-07-05</td></tr></table>")
            prior.write_text("ip\tfinding\tseverity\n10.0.0.5\tA\tMEDIUM\n")
            result = run_report(source, output, "--prior", str(prior))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((output / "summary.json").read_text())["comparison"]["recurring"], 1)

    def test_legacy_pat_prior_headers_are_normalized(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base / "current.xlsx"; output = base / "out"
            rows = [HEADERS,
                ["Lifebit-Synapxe", "MEDIUM", "100.123.206.201", "nginx 1.3.0 < 1.28.2 / 1.29.x < 1.29.5 SSL Upstream Injection", "", "Recast", "2026-07-19"],
                ["Lifebit-Synapxe", "HIGH", "100.123.206.111", "new finding", "", "Remediation", "2026-07-19"]]
            write_xlsx(source, rows)
            result = run_report(source, output, "--prior", str(FIXTURES / "legacy-prior-shape.tsv"))
            self.assertEqual(result.returncode, 0, result.stderr)
            comparison = json.loads((output / "summary.json").read_text())["comparison"]
            self.assertEqual(comparison, {"compatible": True, "key": "ip|finding|normalized_severity", "recurring": 1, "new_or_changed": 1, "prior_only": 1})


if __name__ == "__main__":
    unittest.main()
