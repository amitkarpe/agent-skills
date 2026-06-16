# HTML Generative UI Plan

Purpose: improve `web-html-page`, `visual-explainer`, and `deep-work` output quality without adding React, CDN assets, remote dependencies, or heavy templates.

## Recommendation

Use a static component-catalog model, not a full Generative UI framework.

For this repo, "Generative UI" should mean:

- Codex chooses from approved local HTML/CSS blocks.
- Reports stay self-contained, offline-safe, and publishable under `/opt/agent-web`.
- Skills compose pages from small reusable blocks instead of inventing layout and CSS every time.

Do not add Vercel AI SDK, LangGraph UI, CopilotKit, or MCP Apps for these report skills yet. Those are useful for real interactive apps, but they are too heavy for local static HTML reports.

## Target Shape

Add a small shared block catalog later:

```text
skills/html-shared/
  blocks/
    status-card.html
    evidence-table.html
    timeline.html
    comparison-matrix.html
    architecture-map.html
    command-block.html
    quiz-card.html
  css/
    readability.css
```

The catalog should be copied or embedded into final HTML. It must not require external CSS, JS, fonts, images, CDN, or a build step.

## Skill Use

`web-html-page`:

- quick report template
- 3-5 blocks per page
- status card, TLDR, evidence table, risk box, next action
- screenshot QA optional

`visual-explainer`:

- visual report template
- card maps plus SVG arrows/connectors
- HTML/CSS cards for long labels
- avoid raw SVG long labels unless wrapping is handled
- screenshot QA required when Amit will visually review it

`deep-work`:

- durable dashboard/portal template
- sections for timeline, glossary, command cookbook, quiz, flashcards
- shared readability rules across all pages
- screenshot QA required when Amit will visually review it

## Why Not Full Generative UI Frameworks

Vercel AI SDK UI, LangGraph Generative UI, CopilotKit, and MCP Apps are better for interactive React or agent apps. The current skill outputs are static local HTML reports. A framework would add setup cost, runtime assumptions, and token overhead without solving the immediate readability problem.

## First Patch To Ask Worker For

Implement only the lightweight component-catalog foundation:

- add `skills/html-shared/README.md`
- add 5-7 tiny reusable block examples
- add one shared `readability.css` snippet
- update the three HTML skills to reference the catalog
- keep all existing templates working
- do not introduce a build system
- do not add external assets
- do not consolidate the three skills

Validation should include:

- `scripts/check-skill-repo.sh`
- `git diff --check`
- external URL scan for changed templates and shared snippets
- browser/screenshot check only if a representative visual/deep sample is generated

## Deferred

- React app
- Vercel AI SDK integration
- LangGraph/CopilotKit integration
- MCP Apps
- JavaScript-heavy runtime composition
- large design system
