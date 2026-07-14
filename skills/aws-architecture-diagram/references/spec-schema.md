# JSON Specification Guide

The JSON specification is the architecture contract and the source of truth for generation. Keep stable IDs across revisions.

## Top-level fields

| Field | Required | Purpose |
|---|---:|---|
| `id`, `name`, `title` | yes | Stable identity and display title |
| `alt_text` | yes for new diagrams | Concise, architecture-specific accessibility summary; legacy omission warns and strict validation fails |
| `long_description` | no | Longer accessible explanation of boundaries, components, and important flows |
| `subtitle` | no | Scope or primary message |
| `architecture_type` | yes | overview, application, deployment, integration, network, devops, security, data-flow, current-state, or target-state |
| `audience` | yes | Intended reader |
| `status` | no | draft, current, proposed, target, deprecated |
| `source_evidence` | yes | User statements, documents, inventories, or assumptions |
| `page` | yes | width, height, background |
| `theme` | no | `aws-clean-2026` by default |
| `icon_mode` | no | `auto`, `official`, `native`, or `fallback`; default `auto` |
| `edge_color_mode` | no | `source`, `semantic`, `target`, or `explicit`; default `source` |
| `boundary` | no | Outer AWS/Region/VPC shell |
| `groups` | no | Accounts, AZs, subnets, tiers, security, operations, external areas |
| `nodes` | yes | Actors, AWS services, and external systems |
| `edges` | no | Directed relationships |
| `annotations` | no | Notes and explanatory text |
| `legend` | no | `auto`, `false`, or explicit legend object |
| `footer` | no | Owner, status, date, note |

## Accessibility

Write `alt_text` as a useful standalone summary of what the diagram shows and
its primary flow. Use 40-500 characters. Do not use placeholders such as
`diagram`, `architecture diagram`, `TBD`, or `TODO`.

Use `long_description` when the important boundaries, sequence, failure path,
or state distinctions need more detail than the concise alt text can carry.
The generator stores both values in draw.io metadata. The review pipeline adds
the same text to deterministic SVG `<title>` and `<desc>` elements and records
the accessible SVG transformation separately from the raw renderer export.

## Page

```json
{
  "page": {
    "width": 1920,
    "height": 1080,
    "background": "#FFFFFF"
  }
}
```

Use 1920 × 1080 for the default 16:9 view.

## Boundary and groups

```json
{
  "id": "vpc",
  "label": "VPC 10.0.0.0/16",
  "kind": "vpc",
  "geometry": [50, 250, 1500, 720],
  "fill": "#F7FBF7",
  "stroke": "#2E7D32",
  "dashed": false,
  "label_align": "left"
}
```

Supported group kinds include `aws-cloud`, `account`, `region`, `vpc`, `availability-zone`, `public-subnet`, `private-app-subnet`, `private-db-subnet`, `security`, `operations`, `external`, and `tier-panel`.

The generator creates separate transparent label cells. Use `label_geometry` only when the automatic protected title band is insufficient.

## Nodes

```json
{
  "id": "alb-a",
  "provider": "aws",
  "label": "Application Load Balancer",
  "icon_key": "elastic-load-balancing-application-load-balancer",
  "native_icon": "application_load_balancer",
  "icon_mode": "auto",
  "variant": "icon-above",
  "geometry": [420, 390, 160, 110],
  "stroke": "#2E7D32",
  "fill": "none",
  "accent": "#2E7D32",
  "font_size": 15,
  "icon_size": 58,
  "state": "current"
}
```

### Node fields

- `provider`: `aws`, `external`, or `vendor`.
- `icon_key`: canonical key for the prepared official AWS icon catalogue.
- `native_icon`: tested `mxgraph.aws4` resource name for native fallback.
- `icon`: local fallback filename, permitted only with explicit fallback mode.
- `variant`: `icon-above`, `icon-left`, or `label-only`.
- `geometry`: `[x, y, width, height]`.
- `fill`: colour or `none`.
- `stroke`: visible card border. Use `none` for a transparent icon/label endpoint.
- `accent`: connector colour when `color_mode` is `source`.
- `font_size`, `font_color`, `font_style`, `icon_size`.
- `state`: `current`, `planned`, `unknown`, or `deprecated`.
- `label_geometry`: optional explicit transparent label position.
- `icon_geometry`: optional explicit icon position.

Use `icon-above` for compact AWS services inside subnets. Use `icon-left` for process cards and detailed flows.

## Edges

```json
{
  "id": "alb-to-app-a",
  "source": "alb-a",
  "target": "ec2-a",
  "caption": "Forward request",
  "kind": "request",
  "color_mode": "source",
  "stroke_width": 2.8,
  "exitX": 0.5,
  "exitY": 1,
  "entryX": 0.5,
  "entryY": 0,
  "caption_geometry": [450, 505, 140, 28]
}
```

### Edge fields

- `kind`: `request`, `data`, `event`, `control`, `security`, `observability`, `replication`, or `planned`.
- `color_mode`:
  - `source`: use source node `accent` or `stroke`;
  - `target`: use target accent;
  - `semantic`: use the edge-kind palette;
  - `explicit`: require `color`.
- `dashed`: overrides the edge-kind default.
- `points`: orthogonal waypoints such as `[[700, 300], [1100, 300]]`.
- `exitX`, `exitY`, `entryX`, `entryY`: perimeter anchor fractions.
- `caption`: concise verb or payload.
- `caption_geometry`: strongly recommended for important or long routes.
- `unlabeled_reason`: required when `caption` is omitted.

## Annotations

Annotations are transparent text by default. They may optionally have a box:

```json
{
  "id": "note",
  "text": "Primary request path",
  "geometry": [700, 180, 260, 28],
  "font_size": 14,
  "color": "#475569",
  "align": "center",
  "box": false
}
```

## Explicit legend

```json
{
  "legend": {
    "show": true,
    "title": "Legend",
    "geometry": [1540, 760, 330, 220],
    "items": [
      {"type": "box", "label": "Public subnet", "stroke": "#2E7D32", "fill": "#F0F8F1"},
      {"type": "box", "label": "Private app subnet", "stroke": "#2563EB", "fill": "#EFF6FF"},
      {"type": "line", "label": "Primary flow", "color": "#2563EB", "dashed": false},
      {"type": "line", "label": "Supporting flow", "color": "#64748B", "dashed": true}
    ]
  }
}
```

## Review metadata

The spec itself does not need pass numbers. `build_and_review.py` records them in the output directory. Apply visual changes to the spec between pass 1 and pass 2 and pass a concise `--changes` description during pass 2.
