---
name: visual-explainer
description: medium visual html explanation reports for architecture, workflows, sequences, resource relationships, ami boxes, plan proposals, option comparisons, before/after maps, and explain visually requests. use when the user needs understanding through diagrams, inline svg, concept-to-real-resource mapping, or aws relationships. richer than web-html-page, lighter than deep-work. avoid durable learning dashboards.
---

# Visual Explainer

Create medium-weight visual HTML reports that explain a technical idea, workflow, architecture, plan, or before/after change.

Before creating HTML, follow `DESIGN.md` exactly. The required design is
Midnight Visual: dark-only, diagram-friendly, and never a white/day theme.

## Use this skill for

- Prompts containing: `explain visually`, `visual explainer`, `architecture diagram`, `workflow diagram`, `AMI box`, `plan proposal`, `compare options`, `show sequence`, `before/after`.
- Understanding system design, resource relationships, build flows, deployment sequences, or decision logic.
- A report that needs diagrams but not a large durable DD learning dashboard.

## Do not use this skill for

- Fast operational summaries. Use `web-html-page`.
- Long-term study artifacts, multi-page learning, flashcards, or research synthesis. Use `deep-work`.
- Plain quick reports that only need tables, bullets, and evidence. Use `web-html-page`.

## Output contract

- Publish to `/opt/crypto-web/demos/<slug>/index.html`.
- Return `http://home/demos/<slug>/`.
- Store source and evidence under
  `~/.AGENTS-temp/<project-or-repo>/<current-lane>/visual-explainer/`.
- Validate the exact URL with `curl -fsSI` before reporting success.
- Default lifecycle: archive after 30 days unless marked `keep`.
- Keep historical pages in place; never use their paths for new output.

Recommended publish command after rendering `output.html`:

```bash
python3 scripts/publish_html.py output.html \
  --skill visual-explainer \
  --project <repo> \
  --slug <slug>
```

## Visual report shape

Use only the components needed:

1. Hero with the problem and the mental model.
2. Snapshot cards for key facts.
3. Inline SVG diagram as the default visual method.
4. Concept-to-real-resource mapping when examples exist.
5. Workflow, sequence, decision tree, or before/after map.
6. Risks, unknowns, and validation evidence.
7. Short recap or action checklist.

For AWS examples, separate concept from real resources. If a real ID, ARN, IP, AMI ID, instance ID, account ID, or tag is unavailable, mark it `unknown / needs refresh`. Never invent realistic identifiers.

## Diagram guidance

Prefer inline SVG or CSS diagrams. Use Mermaid only if vendored locally or explicitly requested. Do not use remote CDN assets.

For architecture-design method choice, Kiro/Python `diagrams`, Graphviz/DOT,
and five-block presentation rules, read:
`docs/ARCH_DESIGN_DIAGRAM_GUIDE.md`.

Useful patterns:

- Workflow: trigger → build → test → promote → deploy → cleanup.
- Architecture map: environment boundary → service/resource cards → arrows.
- AMI box: base AMI → hardening/tools → custom AMI → launch template → EC2.
- Sequence flow: actor → system → service → result.
- Decision tree: condition → option → risk → recommendation.

## Safety rules

- No secrets, credentials, tokens, private keys, or unmasked sensitive data.
- Sanitize or mask AWS account-sensitive values by default.
- Label examples clearly as `example`, `placeholder`, or `unknown`.
- Keep the report self-contained, offline, and local LAN safe.

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

See `references/visual-patterns.md`, `references/aws-resource-safety.md`, and `assets/visual-explainer-template.html` only when needed.
