# Web HTML Page Design: Midnight Compact

`web-html-page` must produce compact dark operational reports.

## Required Theme

- Theme name: `Midnight Compact`.
- Default is dark only.
- Do not add a day, light, or white theme.
- Do not add a theme toggle.
- Body background must be dark, preferably `#0f172a`.
- Panels, cards, tables, and code blocks must stay dark.

## Visual Style

- Small operational report, not a dashboard or landing page.
- Constrained width around 980-1040px.
- Use quiet dark panels, clear borders, compact cards, simple tables, and status badges.
- Use blue/cyan sparingly for identity, links, and status highlights.
- Keep headings compact and work-focused.
- Inline SVG is allowed only when it improves scan speed.

## Readability Gate

- Do not use text-shadow, text stroke, glow, blur, embossed text, or low-contrast decorative text.
- Body text must be at least 16px.
- Card, badge, table, and diagram labels must be at least 15px unless the text is non-critical metadata.
- Critical text must use high contrast against its panel.
- Warning, error, and success boxes must not use dark gray text on dark colored panels.
- Normal reports must not create a horizontal scrollbar at 1366px width.
- Prefer wrapping or stacking cards over ultra-wide tables or diagrams.

## Conditional Screenshot QA

- Screenshot/browser QA is optional for quick reports.
- If screenshot/browser QA is run, check that text is readable on a laptop screenshot and that there is no horizontal scroll.

## Forbidden

- No default white body background.
- No `background:white`, `background:#fff`, or day-theme body styles outside print CSS.
- No external CSS, JS, fonts, images, or CDN assets.
- No decorative gradients that turn the report into a marketing page.
- No large hero layouts.

## Safety

- Keep reports self-contained and offline-safe.
- Sanitize secrets, tokens, keys, account-sensitive values, and raw logs.
- Use `unknown / needs refresh` for unknown real IDs.
