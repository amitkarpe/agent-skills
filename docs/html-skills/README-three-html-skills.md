# Codex HTML Skills Bundle

This bundle contains exactly three skills:

1. `web-html-page` - small, fast operational HTML reports.
2. `visual-explainer` - medium visual explanation reports and diagrams.
3. `deep-work` - heavy durable DD learning dashboards.

Copy the three skill folders into:

`~/.codex/skills/`

## How to ask Codex

### web-html-page

Use when you want a quick browser report after work:

- `Use web-html-page. Show me what changed in browser.`
- `Create a web report for this worker result.`

### visual-explainer

Use when you need visual understanding:

- `Use visual-explainer. Explain this AMI workflow visually.`
- `Create an architecture diagram and decision map.`

### deep-work

Use when you want a durable DD learning artifact:

- `Use deep-work. Show this into DD.`
- `Create a deep dashboard for this architecture and lifecycle.`

## Output destinations

- `web-html-page` and `visual-explainer`: `/opt/agent-web/<project-or-repo>/<current-lane>/`
- `deep-work`: `/opt/agent-web/deep/<category>/<topic>/`

## Evidence destinations

- `web-html-page`: `~/.AGENTS-temp/<project-or-repo>/<current-lane>/web-html-page/`
- `visual-explainer`: `~/.AGENTS-temp/<project-or-repo>/<current-lane>/visual-explainer/`
- `deep-work`: `~/.AGENTS-temp/deep-work/<category>/<topic>/`

## Lifecycle

- `web-html-page`: archive or delete after 7 days unless marked keep.
- `visual-explainer`: archive after 30 days unless marked keep.
- `deep-work`: never auto-delete.

## Safety baseline

All HTML must be self-contained, offline-safe, and local-LAN safe. Do not leak secrets. Do not invent real AWS IDs. Prefer inline SVG for diagrams.
