# Visual Explainer Patterns

## Choose one primary visual

Pick the visual that reduces reading fastest:

- Workflow: ordered process or pipeline.
- Architecture map: components and relationships.
- Sequence flow: request/response or actor/system flow.
- Decision tree: branching choices.
- Before/after map: compare old and new states.
- Concept-to-resource mapping: explain abstract concept beside real example.

## Concept-to-real-resource layout

Use a two-column layout:

- Left: concept explanation in plain language.
- Right: real resource evidence or example.

If real data is unavailable, use `unknown / needs refresh`. Do not fabricate resource IDs.

## Diagram rules

- Inline SVG first.
- Keep arrows meaningful.
- Use environment boundaries for AWS accounts or stages.
- Use short labels inside boxes.
- Put details in nearby callouts or collapsibles.
