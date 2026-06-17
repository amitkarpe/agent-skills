# JSON Spec Examples

Use the sample specs in `examples/sample.spec.json` as the minimal pattern.

## What the AI should generate

Only generate the JSON spec: title, component names, props, and child order.

## What the renderer owns

The renderer owns:

- HTML shell
- CSS variables and dark theme
- spacing and layout
- SVG/diagram scaffolding
- badges, cards, tables, and print CSS
- escaping/sanitization

## Token-saving rule

Do not ask the AI to regenerate repeated CSS, shell, nav, badge, table, or diagram boilerplate. Let the renderer expand small semantic specs into rich HTML.
