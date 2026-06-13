# DD Deep Work Dashboard Patterns

## Core components

Use the smallest set that creates deep understanding:

- Hero thesis and 30-second view.
- Sticky nav with separate utility row (search + theme toggle).
- Snapshot cards.
- Concept map or architecture diagram.
- Workflow or lifecycle.
- Decision guide or comparison matrix.
- Collapsible deep dives (single-page only — never in all-in-one.html).
- Glossary.
- Flashcards and reveal quiz.
- What-to-remember panel.

---

## Portal nav pattern

When building a portal (multiple pages), every page must share this nav shell:

```html
<header style="background:linear-gradient(135deg,#111827,#1a1d27);border-bottom:1px solid #2a2d3e;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:34px;height:34px;background:#4f8ef7;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px">🏭</div>
    <div>
      <div style="font-size:16px;font-weight:700">PORTAL NAME</div>
      <div style="font-size:11px;color:#8892a4">SUBTITLE · ENV CHIP</div>
    </div>
  </div>
  <nav style="display:flex;gap:6px;flex-wrap:wrap">
    <!-- One <a> per page. Add class="active" on the current page. -->
    <a href="index.html" style="background:#1e2130;border:1px solid #2a2d3e;padding:4px 10px;border-radius:6px;font-size:11px;color:#8892a4;text-decoration:none">Home</a>
    <a href="architecture.html" style="...">Architecture</a>
    <!-- ... -->
  </nav>
</header>
```

Active page style override:
```css
nav a.active { background: #4f8ef7; color: #fff; border-color: #4f8ef7; }
```

Rules:
- Nav must be identical on every page (same links, same order).
- Only the `class="active"` attribute changes per page.
- Nav must include `all-in-one.html` as the last link, labelled "📄 Export".

---

## Version watermark (required on every page)

Add to every page footer:

```html
<footer style="border-top:1px solid #2a2d3e;padding:12px 24px;text-align:center;color:#8892a4;font-size:11px">
  PORTAL NAME · v<DATE> · <ENV> · Generated from evidence dated <EVIDENCE-DATE> · TTL <TTL>
</footer>
```

The date must be the actual generation date (not a placeholder).
If evidence has a known staleness date, include: `· evidence current as of <date>`.

---

## Export-safe rules (all-in-one.html)

These rules are MANDATORY in `all-in-one.html`. Recommended everywhere.

| Rule | Why |
|------|-----|
| No `<details>`/`<summary>` | Pandoc silently drops content inside them |
| No `display:none` or JS-toggled visibility | Content disappears in docx |
| No `position:sticky` nav | Breaks in print/docx |
| All sections flat and open | Ops should see everything without clicking |
| Diagrams as `<img>` with base64 src | Survives Pandoc conversion |
| `<h1>` = portal title, `<h2>` = page title, `<h3>` = section | Pandoc maps these to Word heading styles |
| Cover page as first `<section>` | Title, version, owner, env, generated date |

Cover page template:
```html
<section style="padding:40px 24px;border-bottom:2px solid #2a2d3e;margin-bottom:32px">
  <h1>PORTAL NAME — Full Reference</h1>
  <table>
    <tr><th>Version</th><td>v2026-06-13</td></tr>
    <tr><th>Generated</th><td>2026-06-13</td></tr>
    <tr><th>Owner</th><td>Amit / CC</td></tr>
    <tr><th>Environment</th><td>DEV 672172129528 / PROD 021577063369</td></tr>
    <tr><th>TTL</th><td>Review by 2026-12-13</td></tr>
  </table>
</section>
```

---

## Theme standard

- Midnight default (`--bg:#0f1117`).
- Contrast optional through compact icon-only toggle.
- Do not add many themes unless explicitly asked.
- Portal pages use the same CSS variable set — define once in a comment block at the top.

---

## Search standard

- Global search: include for large dashboards and index pages.
- Scope: search only highlights — never hides non-matching content (hides content breaks print).
- Keep search input separate from nav row so it never overlaps section links.

---

## CommandBlock standard

```html
<div style="background:#020617;border:1px solid #2a2d3e;border-radius:8px;overflow:hidden;margin:8px 0">
  <div style="display:flex;justify-content:space-between;align-items:center;background:#111827;padding:6px 10px">
    <span style="font-size:11px;color:#8892a4">PURPOSE OF COMMAND</span>
    <button onclick="navigator.clipboard.writeText(this.dataset.copy)"
            data-copy="COMMAND HERE"
            style="background:#1e2130;border:1px solid #2a2d3e;color:#fff;border-radius:6px;padding:3px 8px;cursor:pointer;font-size:10px">Copy</button>
  </div>
  <pre style="margin:0;padding:10px;font-family:'Courier New',monospace;font-size:11px;color:#93c5fd;overflow-x:auto">COMMAND HERE</pre>
</div>
```

Rules:
- `data-copy` must contain only the command, not the label.
- No shell prompt prefix (`$`, `#`) in the command body.
- Add expected output in a separate `<pre>` block below when useful.
- Copy buttons are required on every CLI block on every page — not just the main dashboard.

---

## index.html pattern (portal entry point)

The portal `index.html` must include:
- Hero: portal name, one-paragraph purpose, environment chips
- Navigation cards: one card per page with title, icon, 1-line description, and link
- Quick status snapshot: key facts at a glance (current AMI IDs, last updated, pending actions)
- Do NOT duplicate the full content of other pages — just link to them

```html
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px">
  <a href="architecture.html" style="background:#1e2130;border:1px solid #2a2d3e;border-radius:10px;padding:16px;text-decoration:none;display:block">
    <div style="font-size:20px;margin-bottom:6px">🗺️</div>
    <div style="font-weight:700;color:#e0e4f0;margin-bottom:4px">Architecture</div>
    <div style="font-size:12px;color:#8892a4">Account boundary, E2E swimlane, AMI lineage</div>
  </a>
  <!-- repeat for each page -->
</div>
```
