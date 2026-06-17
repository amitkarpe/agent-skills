# Component Catalog

This is the human-readable catalog for the deterministic JSON renderer. The machine-readable catalog is `component-catalog.json`.

## Model

- The AI chooses components and fills props.
- The Python renderer maps component types to fixed HTML/CSS/SVG.
- Unknown components are rejected by `scripts/validate_spec.py`.
- The renderer may support components used by sibling HTML skills; this skill's
  `component-catalog.json` is the allowlist for what may be used here.

## Available components

- **Page**: Root page shell.
- **Hero**: Compact title and status header.
- **TLDR**: 3-6 short summary bullets.
- **StatusCards**: Small metric/status cards.
- **EvidenceTable**: Compact evidence/checks table.
- **RiskBox**: Risks/blockers grouped by severity.
- **NextAction**: Single next action or short action list.
- **Timeline**: Short ordered timeline.
- **Checklist**: Simple checklist.
- **Section**: Generic titled section container.

## Component rules

- `Page` should be the root element.
- `Hero` should usually be the first child.
- Keep tables narrow and rows concise.
- Use `unknown / needs refresh` instead of inventing AWS IDs, ARNs, IPs, AMI IDs, or account IDs.
- Do not include raw HTML or external URLs in props.
