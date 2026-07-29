---
name: deep-work
description: premium dd deep work dashboards for durable learning, dense technical concepts, long research, multi-source synthesis, architecture reviews, cloud/aws/devops workflows, timelines, lifecycles, command cookbooks, glossary, flashcards, quizzes, and study mode. use when user says dd, deep-work, deep dashboard, learning dashboard, explain deeply, absorb this, compare research, or multi-page dashboard. not for quick task summaries.
---

# Deep Work

Create premium DD Deep Work dashboards for long-term learning and durable technical understanding.

Before creating HTML, follow `DESIGN.md` exactly. The required design is
Midnight Portal: dark by default, with optional contrast-dark only and no
white/day screen theme.

## Use this skill for

- Prompts containing: `DD`, `deep-work`, `deep dashboard`, `learning dashboard`, `explain deeply`, `absorb this`, `study mode`, `compare research`, `multi-page dashboard`, `portal`, `ops portal`, `kb portal`.
- Dense technical topics, codebases, architecture reviews, research, cloud/AWS/DevOps concepts, incident lessons, lifecycle learning, and long notes.
- Cases where the user wants to understand the same material through multiple visual forms.

## Do not use this skill for

- Quick operational reports. Use `web-html-page`.
- Medium visual diagrams or plan explanations. Use `visual-explainer`.

---

## Output modes

### single-page mode (default)

One self-contained HTML file per topic.

- Preferred new publishing root is `/opt/agent-web/www/`.
- Prefer publishing through `/opt/agent-web/bin/agent-report` when available.
- Preferred URL shape is `http://192.168.0.9/www/reports/deep-work/<YYYY>/<MM-DD>/<slug>/index.html`.
- Compatibility publish path remains `/opt/agent-web/deep/<category>/<topic>/<slug>.html`.
- Store evidence in `~/.AGENTS-temp/deep-work/<category>/<topic>/`
- Default always: print the LAN URL form from `agent-report` when used, otherwise print the compatibility URL.
- Use Tailscale URL `http://100.72.42.94/deep/<category>/<topic>/<slug>.html` only when Amit explicitly says office or Tailscale.
- Lifecycle: never auto-delete. These are durable learning artifacts.

Recommended publish command after rendering `output.html`:

```bash
/opt/agent-web/bin/agent-report \
  --type deep-work \
  --title "Deep Work Topic" \
  --slug report-slug \
  --html-file output.html \
  --evidence "$EVIDENCE_DIR" \
  --owner "${USER:-agent}" \
  --update-index yes
```

Keep `/opt/agent-web/deep/...` compatibility paths for existing deep portals and do not bulk-migrate old learning dashboards.

### portal mode

Use when the output is more than one page, or when the user says "portal", "kb portal", "multiple pages", or "ops portal".

A portal is a named set of pages under a shared prefix with:
- A stable entry point: `index.html`
- Shared nav present on every page (same 6-link bar, active page highlighted)
- Shared CSS design system (inline per page — no external stylesheet)
- A version watermark on every page: `v<YYYY-MM-DD> · <topic> · <environment>`
- Stable filenames with no date suffix (e.g. `architecture.html`, not `architecture-20260612.html`)
- An `all-in-one.html` for offline/export use (see export mode below)

Portal file structure:
```
/opt/agent-web/www/reports/deep-work/<YYYY>/<MM-DD>/<slug>/portal/
  index.html          ← entry landing page (hero, 30-sec view, nav cards to all pages)
  architecture.html
  inventory.html
  ami-boxes.html      ← example; name pages for the topic
  resource-kb.html
  runbook.html
  all-in-one.html     ← export-safe concatenation of all pages
```

Compatibility portal paths under `/opt/agent-web/deep/<category>/<topic>/portal/` remain valid when an older workflow or link expects them.

When building a portal:
1. Decide all page names before writing any HTML.
2. Write the shared nav fragment first (list of `{filename, label}` pairs).
3. Build each page using the same header/nav/footer shell.
4. Build `all-in-one.html` last by concatenating page bodies under flat headings.
5. Run self-review gate before writing result packet.

---

## Export mode (`all-in-one.html`)

Use when the user mentions: "docx", "Word", "print", "share offline", "Confluence", "SharePoint", "6 months from now", or "durable copy".

Export-safe HTML rules (required in `all-in-one.html`, recommended in all pages):
- Use only semantic tags: `<h1>`–`<h3>`, `<table>`, `<pre>`, `<ul>`, `<ol>`, `<p>`
- **Never use `<details>`/`<summary>`** — Pandoc silently drops their content
- All content shown open and flat — no JS-toggled visibility
- Diagrams embedded as `<img src="data:image/png;base64,...">` or inline SVG
- Cover page at top: title, version, generated date, owner, environment, TTL

Convert to docx:
```bash
pandoc portal/all-in-one.html \
  --from html --to docx \
  --output "AMI-Factory-Ops-KB-v$(date +%Y%m%d).docx"
```

---

## Dashboard shape (single-page)

Use the smallest set that creates deep understanding:

1. Hero thesis and 30-second view.
2. Sticky navigation with compact utility controls (search, theme toggle).
3. Snapshot cards.
4. Concept map or architecture map.
5. Workflow, lifecycle, timeline, or sequence.
6. Comparison matrix or decision guide.
7. Deep dives using collapsible sections.
8. Glossary, flashcards, quiz, and what-to-remember section.
9. Optional command cookbook with copy-safe CommandBlocks.

---

## Architecture Lens

DD is generic first, but architecture-aware. If the prompt mentions architecture, AWS, AMI factory, DEV/PROD, VPC, EC2, AMI, KMS, IAM, SSM, launch templates, deployment flow, or environment boundaries, add an Architecture Lens unless the user asks for a lighter page.

For an AWS Ops deploy portal, follow
`docs/OPS_DEPLOY_PRESENTATION_GUIDE.md`. Keep portal facts aligned with the same
`PROVEN`, `IMPLEMENTED`, `BLOCKED`, and `FUTURE` vocabulary used by the
companion presentation. Prefer Graphviz/DOT for complex deterministic graphs;
use Python `diagrams` when AWS icons materially improve recognition. Keep the
diagram source and generated asset with the evidence bundle.

Architecture Lens decision logic:
- DEV/PROD boundary present → add account boundary diagram
- Build pipeline present → add swimlane (numbered steps, color-coded lanes)
- More than 3 AWS services → add AMI/resource lineage map
- Validation or compliance present → add validation matrix table

For diagram implementation, see `references/architecture-lens.md`.

---

## Design rules

- Default theme: Midnight. Optional compact icon-only toggle to Contrast.
- Use emoji as visual anchors, not decoration overload.
- Keep dense text behind collapsible deep dives (except in `all-in-one.html`).
- Version watermark in every page footer: `v<date> · <topic> · <env chip>`
- CLI code blocks must have copy buttons on every page, not just the main dashboard.
- No CDN, external JS, remote fonts, or remote images. Ever.

---

## Safety rules

- Do not leak secrets, credentials, private keys, tokens, session data, or production-sensitive values.
- Do not invent real AWS IDs. Unknown IDs must be labeled `unknown / needs refresh`.
- Sanitize account IDs and credential-like values unless the user explicitly approves keeping them.
- Separate concept examples from real resource evidence.

---

## Self-review gate

Before writing the result packet, verify every page in the output:

```
☐ All nav links resolve to real files in this portal (no 404s)
☐ No <details>/<summary> in all-in-one.html or any export-safe page
☐ Version watermark present in footer of every page
☐ No invented AWS IDs — any ami-[a-f0-9]+ not in evidence is labelled unknown
☐ CLI code blocks have copy buttons
☐ At least one real diagram on the architecture page (not just a table)
☐ No external URLs (CDN, fonts, JS) — grep for https?:// outside LAN ranges
☐ all-in-one.html exists if portal mode was used
☐ index.html is the entry point and links to all other pages
```

If any check fails, fix before writing result.

---

## JSON-spec render path

Prefer deterministic JSON-spec rendering before writing direct HTML.

Use this flow for repeatable reports:

1. Create `report.spec.json` using `references/json-spec-contract.md`.
2. Use only components in `references/component-catalog.json`.
3. Run `scripts/validate_spec.py report.spec.json`.
4. Run `scripts/render_html_from_spec.py report.spec.json output.html`.
5. Run `scripts/validate_html.py output.html`.
6. Publish with `scripts/publish_html.py` only when LAN publishing is requested.

The AI chooses report content, component types, props, and child order. The
renderer owns HTML, CSS, layout, spacing, cards, badges, print CSS, and
escaping.

Direct handwritten HTML is fallback only when the catalog cannot express the
requested page. Fallback HTML must still follow `DESIGN.md` and pass
`validate_html.py`.

---

See `references/dashboard-patterns.md`, `references/architecture-lens.md`, and `assets/deep-work-template.html` for deeper template guidance.
See `agents/claude.yaml` for Claude-specific behaviour overrides.
