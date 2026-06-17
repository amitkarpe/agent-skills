# HTML JSON Renderer Guardrails

Purpose: preserve the approved direction for the three HTML/reporting skills and give future reviewers a clear contract.

Scope:

- `skills/web-html-page/`
- `skills/visual-explainer/`
- `skills/deep-work/`

## Recommendation

Use the JSON-spec renderer as the preferred path for repeatable reports, but keep direct HTML fallback.

Install or update renderer work only after the cleanup gates below are satisfied:

1. Raise renderer CSS label sizes to 15px minimum.
2. Add `text-shadow:none`, `-webkit-text-stroke:0`, `overflow-wrap:anywhere`, and `overflow-x:hidden` in renderer CSS.
3. Clarify `schemas/report.schema.json` role, or wire/remove it.
4. Keep JSON-spec flow as preferred, with direct HTML fallback preserved.
5. Do not consolidate the three skills yet.

## Core Rules

- Generated HTML must be self-contained and offline-safe.
- No CDN, remote fonts, remote JS, remote CSS, remote images, or external browser-fetching assets.
- Body text must be at least 16px.
- Labels, badges, nav text, card labels, table labels, command labels, timeline labels, and diagram text must be at least 15px unless explicitly documented as non-critical metadata.
- Do not use text shadow, text stroke, glow, blur, embossed text, or decorative low-contrast text.
- Avoid page-level horizontal scroll at 1366px width.
- Prefer wrapping, stacking, or card maps over ultra-wide tables and diagrams.
- Warning, error, and success panels must not use dark gray text on dark colored panels.
- Critical text must have high contrast.

## Architecture

The approved model is static generative UI:

- AI generates a compact JSON spec.
- `references/component-catalog.json` defines the allowed components.
- `scripts/validate_spec.py` validates the spec before rendering.
- `scripts/render_html_from_spec.py` renders deterministic offline HTML.
- `scripts/validate_html.py` validates the generated HTML before publish.

The authoritative safety gate is:

- `scripts/validate_spec.py`
- `references/component-catalog.json`

`schemas/report.schema.json` is only an editor/shape hint unless it is explicitly wired into the validator.

## Fallback Rule

Direct handwritten HTML remains allowed when the component catalog cannot express the requested report.

Fallback HTML must still:

- follow `DESIGN.md`
- stay offline/self-contained
- pass `scripts/validate_html.py`
- avoid external assets
- preserve the readability gate

## Skill Boundaries

Keep the three skills separate:

- `web-html-page`: quick operational summaries and evidence reports.
- `visual-explainer`: medium visual explanations, diagrams, workflows, and architecture maps.
- `deep-work`: durable DD dashboards, portals, study artifacts, timelines, glossary, quiz, and deep research.

Do not merge them into one mega-skill.

Do not add React, Vercel AI SDK, LangGraph UI, CopilotKit, MCP Apps, or a build system unless Amit explicitly approves that broader direction.

## Component Catalog Rules

- Extend the catalog before extending renderer behavior.
- Keep components semantic, not low-level layout primitives.
- Prefer components such as `Hero`, `TLDR`, `StatusCards`, `EvidenceTable`, `RiskBox`, `FlowDiagram`, `ArchitectureMap`, `DecisionGuide`, `Timeline`, `Glossary`, `Quiz`, and `CommandBlocks`.
- Unknown components must fail validation.
- Unknown props must fail validation.
- Missing child references must fail validation.
- Cycles must fail validation.
- The root element must exist and have type `Page`.
- Raw HTML, CSS, JavaScript, SVG, iframes, link tags, images, or script tags inside spec strings must fail validation.
- External URL-like strings inside spec content must fail validation by default.
- 12-digit account-like IDs must fail unless `--allow-account-ids` is explicitly used.

The renderer may contain component handlers used by sibling HTML skills. The per-skill catalog is the allowlist for what a specific skill may use.

## Validation Gates

Before commit or push, run:

```bash
python3 -m py_compile \
  skills/web-html-page/scripts/*.py \
  skills/visual-explainer/scripts/*.py \
  skills/deep-work/scripts/*.py

for s in web-html-page visual-explainer deep-work; do
  python3 "skills/$s/scripts/validate_spec.py" "skills/$s/examples/sample.spec.json"
  python3 "skills/$s/scripts/render_html_from_spec.py" "skills/$s/examples/sample.spec.json" \
    "/home/dev/.AGENTS-temp/agent-skills/json-render-smoke/$s.html"
  python3 "skills/$s/scripts/validate_html.py" \
    "/home/dev/.AGENTS-temp/agent-skills/json-render-smoke/$s.html"
done

scripts/check-skill-repo.sh
git diff --check
```

Run negative tests for:

- external URL string
- raw HTML/script/SVG/table string
- 12-digit account-like ID
- unknown component
- unknown prop
- missing child reference
- cycle
- root not `Page`

Run a generated-output scan:

```bash
rg -n "https?://|@import|fetch\\(|XMLHttpRequest|<script[^>]+src=|<link[^>]+href=|url\\(" \
  /home/dev/.AGENTS-temp/agent-skills/json-render-smoke
```

Expected result: no matches.

## Allowed Static Scan Matches

Broad scans over skill source may find expected strings:

- LAN/Tailscale URLs in `SKILL.md`
- JSON Schema `$schema` URL in schema hint files
- regex strings inside `publish_html.py` and `validate_html.py`
- local SVG marker references such as `url(#arr)`

These are not browser-fetching remote assets.

## Future Improvement Policy

- Improve the catalog and examples first.
- Keep renderer behavior deterministic.
- Keep scripts self-contained inside each skill until the pattern proves useful.
- Consider `skills/html-shared/` only after repeated duplication becomes a real maintenance problem.
- Avoid large design-system rewrites.
- Avoid adding frontend framework dependencies to static report skills.
- Keep existing publish/backup/offline safety behavior intact.
