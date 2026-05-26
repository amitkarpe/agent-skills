---
name: agent-web-reporting
description: Create or publish sanitized Amit-friendly static HTML reports to the local LAN web server under /opt/agent-web, returning review URLs such as http://192.168.0.9/td/report.html. Use when Amit asks for HTML reports, web-server URLs, Windows review pages, lane dashboards, or summaries that should be readable in a browser instead of copied to /tmp/dell.
---

# Agent Web Reporting

Use this skill when Amit needs a clean browser-readable report on the local web server.

## Contract

- Publish sanitized static HTML under `/opt/agent-web/<lane>/`.
- Return the LAN URL, not a `/tmp/dell` path.
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
- `amit`
- another clear lowercase lane when requested

## Workflow

1. Gather the final result packet or summary.
2. Write a concise HTML file in the owning evidence area first, for example:
   `~/.AGENTS-temp/<repo>/<topic>/<name>.html`.
3. Sanitize before publishing:
   - no secrets, tokens, keys, `.env`, `.ssh`, wallets, private config, or raw AWS dumps
   - no whole repos or whole temp folders
   - no long logs
   - no unreviewed raw JSON unless summarized
4. Publish with the bundled script.
5. Return the final URL and the durable source path.

## Publish Helper

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

## Output Shape

Final response should include:

```text
Published:
- http://192.168.0.9/<lane>/<file>.html

Source:
- <durable local source html path>
```

If publishing fails, report the reason and the source file path.
