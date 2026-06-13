# Visual Explainer Design: Midnight Visual

`visual-explainer` must produce medium-weight dark visual explanation reports.

## Required Theme

- Theme name: `Midnight Visual`.
- Default is dark only.
- Do not add a day, light, or white theme.
- Body background must be dark, preferably a midnight navy/blue base.
- Panels, diagram boxes, callouts, and cards must stay dark.

## Visual Style

- Richer than `web-html-page`, lighter than `deep-work`.
- Use dark environment boundaries, colored lanes, inline SVG diagrams, and compact callouts.
- Use cyan, indigo, green, amber, and red for meaning, not decoration.
- Diagram labels must be short and readable.
- Keep concept examples separate from real resource evidence.

## Forbidden

- No default white body background.
- No `background:white`, `background:#fff`, or day-theme body styles outside print CSS.
- No CDN Mermaid, remote fonts, external images, or browser-fetched diagram tooling.
- No decorative light-theme cards or marketing hero sections.

## Safety

- Keep diagrams self-contained in HTML.
- Never invent AWS IDs or realistic resource names.
- Mask account-sensitive values unless Amit explicitly approves keeping them.
