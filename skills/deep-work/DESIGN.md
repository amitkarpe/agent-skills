# Deep Work Design: Midnight Portal

`deep-work` must produce durable dark learning dashboards and portals.

## Required Theme

- Theme name: `Midnight Portal`.
- Default is dark.
- Optional toggle may switch only to another dark contrast theme.
- Do not add a day, light, or white screen theme.
- Body background must be dark in normal browser view.
- Cards, portal shells, nav, timelines, command blocks, and deep dives must stay dark.

## Portal Rules

- Portal pages must share the same dark shell and nav.
- Every page must keep the version watermark/footer.
- `all-in-one.html` may include print/export CSS.
- White background is allowed only inside `@media print` for print/export readability.

## Visual Style

- Dense but structured.
- Use sticky dark nav, compact utility controls, dark cards, diagrams, lifecycle timelines, and command cookbooks.
- Use emoji as small visual anchors, not decoration overload.
- Keep long content behind collapsible sections except in export-safe pages.

## Readability Gate

- Do not use text-shadow, text stroke, glow, blur, embossed text, or low-contrast decorative text.
- Body text must be at least 16px.
- Diagram, card, table, command, badge, and timeline labels must be at least 15px unless the text is non-critical metadata.
- Critical text must use high contrast against its panel.
- Warning, error, and success boxes must not use dark gray text on dark colored panels.
- Normal reports must not create a horizontal scrollbar at 1366px width.
- Prefer wrapping or stacking cards over ultra-wide diagrams, timelines, or comparison matrices.

## Conditional Screenshot QA

- Screenshot/browser QA is required for dashboards or portals Amit will review visually.
- If screenshot/browser QA is run, check readable labels, high contrast, and no horizontal scroll.

## Forbidden

- No default white body background.
- No `background:white`, `background:#fff`, or day-theme body styles outside print CSS.
- No remote fonts, CDN JS, remote images, or external diagram runtimes.
- No theme toggle to a white/day palette.

## Safety

- Keep dashboards self-contained and offline-safe.
- Do not leak secrets, tokens, private keys, session data, or production-sensitive values.
- Separate concept examples from real resource evidence.
