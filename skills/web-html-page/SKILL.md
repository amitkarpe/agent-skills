---
name: web-html-page
description: fast low-token static html reports for codex tasks. use when the user says show html, web report, publish report, what changed, summarize task, show me in browser, agent-web-reporting, or asks for a quick operational summary after a worker run. generate small self-contained offline html under /opt/agent-web with evidence in ~/.AGENTS-temp. do not create deep dashboards or rich diagrams.
---

# Web HTML Page

Create small, fast, local HTML reports for operational review after Codex work.

## Use this skill for

- Quick task summaries, worker results, lane status, diffs, reviews, and run evidence.
- Prompts containing: `show html`, `web report`, `publish report`, `what changed`, `summarize task`, `show me in browser`.
- Legacy prompts or docs that say `agent-web-reporting`; this skill is the replacement for quick reports.
- Cases where terminal text is hard to scan but a full dashboard would be wasteful.

## Do not use this skill for

- Rich architecture diagrams or visual teaching. Use `visual-explainer`.
- Durable learning dashboards, research, study mode, or DD. Use `deep-work`.

## Output contract

- Publish HTML to `/opt/agent-web/<project-or-repo>/<current-lane>/<slug>.html`.
- Store source/evidence in `~/.AGENTS-temp/<project-or-repo>/<current-lane>/web-html-page/`.
- Print a LAN URL like `http://192.168.0.9/<project-or-repo>/<current-lane>/<slug>.html`.
- Default lifecycle: archive or delete after 7 days unless marked `keep`.
- `agent-web` remains the web service name; only the old `agent-web-reporting` skill name is retired.
- Old lane-only URLs such as `/td/report.html` are compatibility mode, not the new default.
- Use a slug without `.html`; the helper adds the suffix.

## Report shape

Use a compact static page:

1. Title, timestamp, repo/lane, status badge.
2. TL;DR box with 3-6 bullets.
3. What changed.
4. Evidence and checks.
5. Risks or blockers.
6. Next action.

Keep it small. Prefer summary boxes, simple tables, short timelines, and status badges. Use inline SVG only when it improves scan speed.

## Safety rules

- Never include secrets, tokens, private keys, session cookies, or credential-like values.
- Sanitize AWS account-sensitive values unless the user explicitly asks to keep them.
- Never invent real AWS IDs. If unknown, write `unknown / needs refresh`.
- No CDN, external JS, remote fonts, or external images.
- HTML must be self-contained and safe for local LAN viewing.

## Helper scripts

- Use `scripts/publish_html.py` to copy output into `/opt/agent-web`, write evidence, reject remote assets, back up overwritten output, and print the LAN URL.
- Use `scripts/validate_html.py` before publishing when the page contains copied logs or resource identifiers.
- Use `scripts/archive_old_reports.py` for the 7-day lifecycle policy.

See `references/template-guidance.md` and `assets/report-template.html` only when a template is needed.
