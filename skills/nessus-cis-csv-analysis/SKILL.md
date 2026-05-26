---
name: nessus-cis-csv-analysis
description: Parse and summarize Nessus/Tenable CIS Compliance Remediation Instruction CSV exports, especially host-level HCR reports with Plugin, Plugin Name, Severity, IP Address, DNS Name, Plugin Output, First Discovered, and Last Observed columns. Use when comparing Nessus CIS/HCR findings with AWS Inspector or creating HTML/MOM/action summaries.
---

# Nessus CIS CSV Analysis

Use for Nessus/Tenable CIS compliance CSV exports.

## Workflow

1. Validate the CSV headers include at least `Plugin`, `Plugin Name`, `Severity`, `IP Address`, `DNS Name`, and `Plugin Output`.
2. Treat `Severity=High` with `Result: FAILED` as open failed controls.
3. Treat `Severity=Medium` with `Result: WARNING` as open review/manual controls unless the scanner output proves a hard fail.
4. Treat `Severity=Info` with `Result: PASSED` as fixed/passing evidence.
5. Ignore scanner inventory noise, for example netstat open-port rows, for control counts. Keep it only in a separate `inventory_info` bucket.
6. When comparing with AWS Inspector, explicitly state whether the exact host had a valid Inspector CIS result. Do not compare a skipped or `totalChecks=0` Inspector run as valid.
7. Produce a human summary: counts, High vs Medium controls, risky-but-passing controls, recommended fixes, exception candidates, and evidence paths.

## Script

Run:

```bash
python3 /home/dev/git/agent-skills/skills/nessus-cis-csv-analysis/scripts/nessus_cis_csv_summary.py <csv> --json-out <summary.json>
```

The script outputs deterministic JSON for downstream HTML/report generation.
