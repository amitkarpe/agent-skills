# Component Catalog

This is the human-readable catalog for the deterministic JSON renderer. The machine-readable catalog is `component-catalog.json`.

## Model

- The AI chooses components and fills props.
- The Python renderer maps component types to fixed HTML/CSS/SVG.
- Unknown components are rejected by `scripts/validate_spec.py`.
- The renderer may support components used by sibling HTML skills; this skill's
  `component-catalog.json` is the allowlist for what may be used here.

## Available components

- **Page**: Root dashboard page shell.
- **Hero**: Thesis and 30-second view.
- **NavCards**: Portal/index navigation cards.
- **SnapshotCards**: Key facts at a glance.
- **ConceptMap**: Concept-to-concept map.
- **ArchitectureMap**: Architecture/resource boundary map.
- **Timeline**: Lifecycle/timeline.
- **DecisionGuide**: Decision matrix blocks.
- **Glossary**: Term definitions.
- **Quiz**: Recall quiz.
- **Flashcards**: Study flashcards.
- **CommandBlocks**: Copy-safe command cookbook.
- **RiskRadar**: Failure modes/risk radar.
- **Checklist**: Action/checklist block.
- **Section**: Generic titled deep section.

## Component rules

- `Page` should be the root element.
- `Hero` should usually be the first child.
- Keep tables narrow and rows concise.
- Use `unknown / needs refresh` instead of inventing AWS IDs, ARNs, IPs, AMI IDs, or account IDs.
- Do not include raw HTML or external URLs in props.
