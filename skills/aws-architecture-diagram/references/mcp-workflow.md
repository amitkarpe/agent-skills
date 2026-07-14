# Optional Local Draw.io MCP Workflow

## Role

Use the official local `@drawio/mcp` tool server to accelerate:

- AWS and vendor shape discovery with `search_shapes`;
- immediate browser review with `open_drawio_xml`;
- obstacle-aware connector routing with `routing: libavoid`;
- local multi-page inspection with `list_pages` and `get_page`;
- bounded page replacement with `set_page` after specification reconciliation.

The JSON specification remains canonical. MCP output is a preview or candidate
edit until the accepted change is represented in the JSON specification,
regenerated, validated, and exported through the normal two-pass workflow.

## Install

The supported package is pinned for repeatability:

```bash
bash scripts/install_mcp.sh
bash scripts/mcp_preflight.sh
```

Restart Codex after installation so the new tools are discovered.

## Fast Path

1. Validate or update the architecture JSON specification.
2. Use `search_shapes` only when an AWS/vendor shape is missing or uncertain.
3. Generate the canonical `.drawio` file with the skill scripts.
4. Use `open_drawio_xml` with `routing: libavoid` for immediate browser review.
5. Record accepted visual or relationship changes in the JSON specification.
6. Regenerate and complete exact Desktop export and two-pass review.

## Validated Local Behavior

The pinned `@drawio/mcp@1.4.0` workflow has been exercised with local
`list_pages`, `get_page`, `search_shapes`, and `open_drawio_xml` calls. Shape
search can return both standard AWS4 `resourceIcon` names and direct AWS4
shapes such as Parameter Store. Record the exact shape kind in
`assets/native-aws4-map.json`; do not force a direct shape through the resource
icon wrapper.

`open_drawio_xml` runs through the local MCP process but opens the public
`app.diagrams.net` frontend with the compressed diagram in the URL fragment.
For sensitive, private, or restricted architecture data, skip browser preview
and use draw.io Desktop export plus local image review only.

## Boundaries

- Use local stdio `@drawio/mcp@1.4.0` by default.
- Do not send private architecture diagrams to the hosted MCP endpoint.
- Do not use browser preview for sensitive diagrams; use Desktop-only review.
- Do not make the stateful third-party live-editor server a dependency of this skill.
- Do not treat `set_page` or a browser edit as canonical without specification synchronization.
- MCP does not replace draw.io Desktop export, XML validation, or visual inspection.
