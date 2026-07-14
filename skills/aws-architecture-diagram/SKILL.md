---
name: aws-architecture-diagram
description: create, revise, validate, render-review, and export polished AWS architecture diagrams as editable draw.io XML with SVG and PNG previews. Use for AWS application, network, deployment, DevOps, security, data-flow, current-state, target-state, or reference-style diagrams; for converting requirements, inventories, Terraform, or design notes into diagrams; and for repairing diagrams with stale icons, weak hierarchy, cluttered arrows, missing boundaries, unreadable labels, overlaps, or poor visual quality. Prefer the latest official AWS Architecture Icons, deterministic JSON specifications, transparent labels, source-coloured connectors, legends, and a mandatory two-pass render-review-improve loop before final delivery.
---

# AWS Architecture Diagram

Create diagrams that are technically accurate, editable, visually calm, and presentation-ready. Keep the JSON specification and `.drawio` source canonical. Treat SVG and PNG as rendered review artefacts.

## Python Environment

Bootstrap the pinned user-local environment once:

```bash
bash scripts/bootstrap_python.sh
```

Run Python entrypoints through `scripts/python.sh`. This keeps Pillow, CairoSVG,
and their transitive dependencies isolated from system Python.

## Default Result

Unless the user asks for a different style:

- Produce a **16:9 landscape technical overview** with generous whitespace.
- Use a light background, clear coloured boundaries, restrained fills, and no decorative gradients.
- Use official AWS Architecture Icons when an official icon cache is available.
- Otherwise use draw.io's bundled AWS library only as an explicit, recorded fallback.
- Use transparent standalone text cells. Never place opaque backgrounds behind labels.
- Use 16px or larger service labels and 13px or larger connector captions.
- Use orthogonal connectors with clear arrowheads and deliberate waypoints.
- Colour a connector from its **source node or source tier** unless a semantic flow colour is explicitly more useful.
- Add a legend whenever two or more colours, line styles, or boundary meanings require explanation.
- Split dense systems instead of shrinking text or forcing everything onto one page.

## Required Workflow

Do not stop after generating XML. Complete the full loop.

1. Read the user's evidence and identify the diagram type, audience, scope, and primary message.
2. Read `references/aws-design-guidance.md`, `references/visual-design-system.md`, and `references/quality-contract.md`.
3. Prepare icons:
   - Preferred: latest package from `https://aws.amazon.com/architecture/icons/` using `scripts/prepare_aws_icons.py`.
   - Accepted fallback: draw.io native AWS shapes, recorded as `drawio-native-aws4`.
   - Search the bundled offline registry before guessing a native shape:

     ```bash
     scripts/python.sh scripts/search_aws4_shapes.py "SERVICE OR RESOURCE"
     ```

   - Bundled PNG fallbacks are regression-test assets only.
4. Create or update an evidence-backed JSON specification. Read `references/spec-schema.md`.
   Add meaningful `alt_text` to every new diagram and `long_description` when
   the concise summary cannot explain the important boundaries and flow.
5. Validate the specification:

   ```bash
   scripts/python.sh scripts/validate_spec.py SPEC.json
   ```

6. Run review pass 1:

   ```bash
   scripts/python.sh scripts/build_and_review.py SPEC.json OUTPUT_DIR --name architecture --pass-number 1
   ```

7. Open the exported PNG or SVG and perform the visual review in `references/render-review-loop.md`.
8. Fix the JSON specification, not only the generated XML. At minimum review:
   - text clipping and wrapping;
   - label transparency;
   - icon consistency and provenance;
   - border hierarchy and colour contrast;
   - connector direction, colour, crossings, captions, and arrowheads;
   - page balance, whitespace, and legend clarity.
9. Run review pass 2 and record the applied changes:

   ```bash
   scripts/python.sh scripts/build_and_review.py SPEC.json OUTPUT_DIR --name architecture --pass-number 2 \
     --changes "Describe the visual corrections applied after pass 1"
   ```

10. Finalize only after both passes exist and the last deterministic review passes:

   ```bash
   scripts/python.sh scripts/finalize_diagram.py OUTPUT_DIR --name architecture
   ```

   When only the preview renderer is available, finalization requires explicit acceptance:

   ```bash
   scripts/python.sh scripts/finalize_diagram.py OUTPUT_DIR --name architecture --accept-preview --allow-warnings
   ```

11. Deliver the finalized `.drawio`, SVG, PNG, JSON spec, and review summary.

## Offline AWS4 Shape Discovery

`assets/aws4-shapes.json` is the local AWS4 registry used for deterministic
shape search and validation. Prefer it before MCP because it works without
network access or an MCP session. Search results are candidates, not render
proof: add accepted entries to `assets/native-aws4-map.json` and complete exact
Desktop rendering before delivery.

## Optional Draw.io MCP

The official local draw.io MCP is an accelerator, not the source of truth. Use
it when the offline registry is missing or ambiguous, or for immediate browser
preview, `libavoid` routing, and multi-page inspection. Apply accepted changes
to the JSON specification and regenerate before finalization.

Read `references/mcp-workflow.md` before enabling or using MCP. Do not use the
hosted MCP for private architecture data, and do not use MCP edits as a reason
to bypass the two-pass render review.

## Renderer Rules

- `build_and_review.py` first tries draw.io Desktop CLI for an exact export.
- If draw.io CLI is unavailable, it uses the bundled subset renderer for layout review and marks the result `preview-renderer`.
- Never describe a preview-renderer image as an exact draw.io export.
- Exact draw.io rendering is required for production, customer-facing, compliance, or executive deliverables.
- A preview-reviewed `.drawio` may still be delivered for editing when the limitation is stated clearly.

## Non-Negotiable Quality Rules

- Use only services and relationships supported by user-provided evidence or clearly marked assumptions.
- Keep service icons and text editable; do not flatten the entire diagram into one background image.
- Embed official image bytes when using the official icon mode. Do not reference remote URLs or local paths.
- Preserve stable cell IDs when revising an existing canonical diagram.
- Pair colour with labels or line styles; do not use colour as the only meaning carrier.
- No resource cards, text cells, or captions may overlap unintentionally.
- No connector may cross a service icon or label unless the user explicitly accepts it.
- Every arrow must have a clear direction and either a concise caption or an explicit `unlabeled_reason`.
- Do not expose secrets, account IDs, ARNs, internal hostnames, or sensitive network details unless explicitly required.
- Do not claim success from XML parsing alone. Final delivery requires a rendered-image review record.
- Reject oversized, excessively deep, entity-bearing, or unknown-AWS4 XML before visual review.

## Key References

- `references/icon-policy.md`: official icon and fallback policy.
- `references/visual-design-system.md`: typography, colour, borders, nodes, and connectors.
- `references/render-review-loop.md`: mandatory two-pass visual QA process.
- `references/spec-schema.md`: JSON fields and examples.
- `references/xml-pattern.md`: draw.io XML composition and transparent-label rules.
- `references/chatgpt-project.md`: use from ChatGPT, Codex, and local automation.
- `references/mcp-workflow.md`: optional local official draw.io MCP workflow.
