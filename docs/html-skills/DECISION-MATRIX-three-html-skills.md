# Decision Matrix

| User asks for | Use | Why |
|---|---|---|
| quick status, task summary, worker result, what changed | `web-html-page` | small and low-token |
| visual explanation, workflow, architecture, sequence, comparison | `visual-explainer` | medium visual report |
| DD, deep study, durable dashboard, long research, multi-source synthesis | `deep-work` | heavy learning artifact |

## Boundaries

- `web-html-page` must not become a dashboard.
- `visual-explainer` must not become a durable learning library.
- `deep-work` must not be used for routine task summaries.

## Migration

- Current `agent-web-reporting` maps to `web-html-page`.
- Current `learning-dashboard` maps to `deep-work`.
- Current `deep-work` should be upgraded and kept as premium DD only.

## Helper scripts

Each skill includes:

- `scripts/publish_html.py`: publish to `/opt/agent-web`, store evidence, print LAN URL.
- `scripts/validate_html.py`: block external links and obvious secret leaks.
- `scripts/archive_old_reports.py`: lifecycle cleanup helper.
