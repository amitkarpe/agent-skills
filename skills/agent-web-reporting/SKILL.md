---
name: agent-web-reporting
description: Create or publish sanitized Amit-friendly static HTML reports to the local LAN web server under /opt/agent-web, returning review URLs such as http://192.168.0.9/td/report.html. Use when Amit asks for HTML reports, web-server URLs, Windows review pages, lane dashboards, or summaries that should be readable in a browser instead of copied to /tmp/dell.
---

# Agent Web Reporting

Use this skill when Amit needs a clean browser-readable report on the local web server.

Default: use `templates/genesis-report.html`.
Replace content, keep the local CSS self-contained, and remove unused sections.
Read `DESIGN.md` only when changing the theme, changing the template, or
creating a complex custom report.

## Contract

- Publish sanitized static HTML under `/opt/agent-web/<lane>/`.
- Preserve the URL contract:
  `http://192.168.0.9/<lane>/<file>.html`
- Return the LAN URL, not a `/tmp/dell` path or a local filesystem path only.
- Keep durable source/evidence in the owning repo or `~/.AGENTS-temp/<repo>/`.
- Publish only cleaned summaries, never raw evidence dumps.

Default URL base:

```text
http://192.168.0.9/
```

Default web root:

```text
/opt/agent-web/
```

## Lanes

Use a short lane folder:

- `work`
- `td`
- `tdg`
- `tdm`
- `pat`
- `synapxe`
- `boss`
- `localai`
- `sarvam`
- `amit`
- another clear lowercase lane when requested

Lane rules:

- Use `/opt/agent-web/<lane>/index.html` as the latest dashboard/status page.
- Use `/opt/agent-web/<lane>/<slug>.html` for a named report.
- Use `/opt/agent-web/<lane>/archive/<name>.html` only for snapshots/backups.
- Use `templates/genesis-dashboard.html` for lane dashboard/index pages.
- Slugs should be lowercase and stable, for example:
  `cookbook-pr-proposal-20260603`.
- Do not create duplicate suffixes like `.html.html`.
- Do not change the service port or URL base inside a report task.

## Workflow

1. Gather the final result packet or summary.
2. Write a concise HTML file in the owning evidence area first, for example:
   `~/.AGENTS-temp/<repo>/<topic>/<name>.html`.
3. Reuse `templates/genesis-report.html` by default:
   - navy header with indigo/blue metadata chips
   - Genesis indigo accents (`#6366F1`) and stronger blue accents where useful
   - light background
   - white bordered sections with optional blue left accent
   - system fonts only
   - no external CSS, JS, image, or font dependencies
4. Sanitize before publishing:
   - no secrets, tokens, keys, `.env`, `.ssh`, wallets, private config, or raw AWS dumps
   - no whole repos or whole temp folders
   - no long logs
   - no unreviewed raw JSON unless summarized
5. Publish with the bundled script.
6. Validate the URL with `curl -I` unless the helper already did so.
7. Return the final URL and the durable source path.

## Publish Helper

To create a starter Genesis report source without publishing:

```bash
/home/dev/git/agent-skills/skills/agent-web-reporting/scripts/publish-html-report.sh \
  --new \
  --lane work \
  --slug my-report \
  --title "My Report" \
  --summary "One sentence summary."
```

This writes a starter source file under:

```text
/home/dev/.AGENTS-temp/agent-web-reporting/<lane>/<slug>.html
```

Run:

```bash
/home/dev/git/agent-skills/skills/agent-web-reporting/scripts/publish-html-report.sh \
  --source /absolute/path/report.html \
  --lane td \
  --slug imagebuilder-decision-20260526
```

This writes:

```text
/opt/agent-web/td/imagebuilder-decision-20260526.html
```

and prints:

```text
url: http://192.168.0.9/td/imagebuilder-decision-20260526.html
```

To update a lane landing page:

```bash
/home/dev/git/agent-skills/skills/agent-web-reporting/scripts/publish-html-report.sh \
  --source /absolute/path/index.html \
  --lane td \
  --index
```

To regenerate a simple static lane index after publishing a named report:

```bash
/home/dev/git/agent-skills/skills/agent-web-reporting/scripts/publish-html-report.sh \
  --source /absolute/path/report.html \
  --lane td \
  --slug imagebuilder-decision-20260526 \
  --update-index
```

`--update-index` is optional. It rebuilds `/opt/agent-web/<lane>/index.html`
from the latest published HTML files in that lane. It does not use a database
or service state.

## Lightweight HTML Validation

The helper checks:

- source looks like HTML; fails if not
- no obvious secret patterns; fails if found
- has `<title>`; warns if missing
- has `<h1>`; warns if missing
- has `updated`, `timestamp`, or `generated` text; warns if missing

Keep extra validation local and cheap. Do not add heavy dependencies. Warnings
should improve report quality without breaking older/simple HTML reports.

## HTML Guidance

Keep reports short and decision-grade:

- title
- updated timestamp
- current status
- blocker or result
- evidence links/paths
- next action

Prefer quiet, readable styling:

- normal HTML/CSS, no external CDN dependency
- desktop Chrome first
- no JavaScript unless needed
- no SVG/gradient decoration
- KISS layout: header, summary, evidence, risks, next action
- use 4px-based spacing and stable responsive grids
- use 12px radius for report cards/sections and 6px for buttons/chips/inputs
- use tables for comparisons and exact command blocks for commands
- use status pills consistently:
  - green = done/pass
  - amber = pending/caution
  - red = blocked/fail
- if the report is routine status, avoid repeatedly calling out ignored `.env`
  files; mention `.env` only for secret-safety checks or if tracked/staged

## Output Shape

Final response should include:

```text
Published:
- http://192.168.0.9/<lane>/<file>.html

Source:
- <durable local source html path>
```

If publishing fails, report the reason and the source file path.
