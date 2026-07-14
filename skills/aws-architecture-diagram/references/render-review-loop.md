# Render, Review, Improve Loop

The `.drawio` XML is not the user experience. The rendered diagram is.

## Pass 1

1. Generate and structurally validate the `.drawio` file.
2. Export with draw.io Desktop CLI when available.
3. Otherwise create a subset-renderer SVG/PNG and mark it as a preview.
4. Inspect the image at full size and at approximately laptop width.
5. Record findings in the generated review report.

## Critical visual review checklist

### Readability

- Is the title immediately readable?
- Is every service label readable without zooming excessively?
- Are labels limited to one or two useful lines?
- Are connector captions readable and placed in whitespace?
- Are all text cells transparent?

### Composition

- Is the primary flow obvious within five seconds?
- Are tiers, VPCs, AZs, and subnets visually distinct?
- Is whitespace balanced, or is one side crowded?
- Are external services clearly outside the correct boundary?
- Is the legend easy to find but visually secondary?

### Connectors

- Does each arrow point in the correct direction?
- Does the line colour match the source tier/node or the declared semantic flow?
- Are supporting flows dashed consistently?
- Do lines avoid icons, labels, and titles?
- Are fan-out and cross-zone routes deliberate rather than automatic spaghetti?

### Icons

- Is every AWS service represented by the correct icon?
- Are icon sizes and alignment consistent?
- Is icon provenance recorded?
- Does the diagram avoid mixing visually incompatible icon generations?

## Pass 2

1. Modify the JSON specification to fix all critical and high findings.
2. Regenerate the `.drawio`; do not patch only the PNG.
3. Export and inspect again.
4. Confirm that the fixes did not create new crossings, clipping, or imbalance.
5. Record the changes in the pass-2 manifest.

## Finalization rule

Finalization requires:

- pass 1 and pass 2 artefacts;
- structural validation success on pass 2;
- deterministic quality gate `PASS` on pass 2;
- any remaining warnings are explicitly reviewed and accepted;
- a non-empty description of pass-2 changes;
- exact draw.io renderer for production-grade delivery, or an explicit preview-renderer limitation.
