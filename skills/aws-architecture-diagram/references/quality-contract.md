# AWS Architecture Diagram Quality Contract

## Truth and scope

- Use only resources and relationships supported by supplied evidence.
- Mark assumptions, planned components, unknowns, and out-of-scope elements explicitly.
- Give each diagram one primary message and one intended audience.
- Split overview, deployment, security, and operations views when their messages compete.

## Structure

- Apply AWS hierarchy only where relevant: AWS Cloud → account → Region → VPC → Availability Zone → subnet.
- Use boundaries to communicate trust, ownership, fault isolation, network scope, or deployment scope.
- Do not draw empty or decorative boundaries.
- Keep external services outside the boundary they do not belong to.

## Visual acceptance

- 16:9 landscape unless another format is requested.
- Minimum service label 15px; minimum connector caption 13px.
- Every AWS node has a correct official or explicitly accepted native icon.
- Text and captions use transparent cells without opaque label backgrounds.
- New diagrams include meaningful `alt_text`; rich diagrams add a
  `long_description` when the concise summary cannot explain the primary flow.
- Borders and fills use a restrained tier-based colour system.
- Primary flow is obvious within five seconds.
- No unintended node, label, caption, or legend overlap.
- No connector crosses a service icon, service label, or boundary title.
- Arrowheads, direction, colour, and line style are consistent.
- A legend explains non-obvious colours and line styles.

## Deliverables

- Evidence-backed JSON specification.
- Editable, uncompressed `.drawio` source.
- SVG and high-resolution PNG from the same source or a clearly marked preview renderer.
- Accessible SVG with deterministic `<title>` and `<desc>`, plus raw renderer
  provenance and hashes when the SVG was transformed after Desktop export.
- Two review-pass manifests and a final review summary.
- Icon source and release metadata.

## Final gate

- JSON and XML validators pass.
- All files are portable: no remote image URL or local-path dependency.
- Pass 2 has a non-empty `changes` record.
- The pass-2 rendered image has been inspected.
- Exact draw.io export is required for production/customer-facing delivery.
