# ChatGPT, Codex, and Local Automation

## Recommended repository files

```text
architecture/
├── SPEC.json
├── output/
├── review-notes.md
└── aws-architecture-diagram/   # this skill
```

## Agent instruction

```text
Read the aws-architecture-diagram skill. Build the diagram from SPEC.json.
Do not stop after XML generation. Run pass 1, inspect the rendered PNG/SVG,
record defects, update the specification, run pass 2, finalize, and return the
editable .drawio plus SVG, PNG, spec, and review summary. Use official AWS icons
when available and clearly identify any draw.io-native fallback.
```

## Renderer availability

ChatGPT or Codex may not have draw.io Desktop installed. The skill therefore provides two renderer paths:

- exact draw.io Desktop CLI export;
- a subset preview renderer for geometry, text, colour, and routing review.

The preview renderer is not a replacement for exact draw.io export. For important deliverables, run the final command on Windows, macOS, or Linux with draw.io Desktop available.

## Automation boundary

The deterministic scripts own:

- schema validation;
- XML generation;
- icon embedding/native-shape selection;
- geometry and portability checks;
- preview/export orchestration;
- review manifests and finalization gates.

The AI agent owns:

- architecture interpretation;
- visual inspection of the rendered image;
- judgement about hierarchy and clarity;
- targeted specification changes between review passes.

## Optional MCP

Codex and other local MCP clients may use the official local draw.io tool server
for shape search, browser preview, routing, and page inspection. ChatGPT web/app
should continue to use the uploaded skill and project files unless it gains a
compatible connector. In all cases, keep the JSON specification canonical and
run the deterministic finalization workflow outside the chat surface.
