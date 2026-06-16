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
- Prefer HTML/CSS cards for long labels and use SVG mainly for arrows, lanes, connectors, or compact labels.
- Avoid raw SVG long labels unless wrapping is handled.
- Keep concept examples separate from real resource evidence.

## Readability Gate

- Do not use text-shadow, text stroke, glow, blur, embossed text, or low-contrast decorative text.
- Body text must be at least 16px.
- Diagram, card, lane, badge, and callout labels must be at least 15px.
- Critical text must use high contrast against its panel.
- Warning, error, and success boxes must not use dark gray text on dark colored panels.
- Normal reports must not create a horizontal scrollbar at 1366px width.
- Prefer wrapping or stacking cards over ultra-wide diagrams.

## Conditional Screenshot QA

- Screenshot/browser QA is required for visual reports Amit will review visually.
- If screenshot/browser QA is run, check readable labels, high contrast, and no horizontal scroll.

## Forbidden

- No default white body background.
- No `background:white`, `background:#fff`, or day-theme body styles outside print CSS.
- No CDN Mermaid, remote fonts, external images, or browser-fetched diagram tooling.
- No decorative light-theme cards or marketing hero sections.

## Safety

- Keep diagrams self-contained in HTML.
- Never invent AWS IDs or realistic resource names.
- Mask account-sensitive values unless Amit explicitly approves keeping them.
