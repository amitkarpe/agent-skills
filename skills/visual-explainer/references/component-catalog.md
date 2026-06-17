# Component Catalog

This is the human-readable catalog for the deterministic JSON renderer. The machine-readable catalog is `component-catalog.json`.

## Model

- The AI chooses components and fills props.
- The Python renderer maps component types to fixed HTML/CSS/SVG.
- Unknown components are rejected by `scripts/validate_spec.py`.
- The renderer may support components used by sibling HTML skills; this skill's
  `component-catalog.json` is the allowlist for what may be used here.

## Available components

- **Page**: Root visual report page.
- **Hero**: Problem, mental model, and key chips.
- **ConceptCards**: Key idea cards.
- **FlowDiagram**: Lanes/nodes/edges workflow diagram rendered as CSS/SVG.
- **ArchitectureMap**: Boundary/resource relationship map.
- **DecisionGuide**: Recommended/maybe/avoid decision blocks.
- **Comparison**: Compact option comparison.
- **RiskRadar**: Risks grouped by severity.
- **EvidenceTable**: Evidence/checks table.
- **Checklist**: Action checklist.
- **Section**: Generic titled section container.

## Component rules

- `Page` should be the root element.
- `Hero` should usually be the first child.
- Keep tables narrow and rows concise.
- Use `unknown / needs refresh` instead of inventing AWS IDs, ARNs, IPs, AMI IDs, or account IDs.
- Do not include raw HTML or external URLs in props.
