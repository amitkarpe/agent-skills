# Draw.io XML Pattern

## Layer order

Create cells in this order so the visual stacking remains predictable:

1. page boundaries and group shells;
2. resource endpoint/card cells;
3. connectors;
4. icons and service labels;
5. connector captions;
6. boundary labels, annotations, title, legend, and footer.

## Boundary pattern

Represent a VPC, Availability Zone, subnet, or tier with two sibling cells:

1. `boundary-shell` or `group-shell`: empty rounded rectangle with fill and stroke.
2. `boundary-label` or `group-label`: transparent text cell placed in a protected title band.

Do not place the label as the shell's value when precise positioning is important.

## Resource pattern

Represent each resource with separate siblings:

1. `resource-card`: the connector endpoint; it may be visible or transparent.
2. `resource-icon`: embedded image or native draw.io AWS shape.
3. `resource-label`: transparent text cell.

Embedded icon style:

```text
shape=image;imageAspect=0;aspect=fixed;image=data:image/svg+xml,...;
```

Do not insert `;base64` inside a draw.io style property. Semicolons delimit
style properties, so draw.io Desktop truncates the image URI. The payload is
still base64-encoded; draw.io uses the comma form shown above.

Native draw.io AWS style:

```text
shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.route_53;aspect=fixed;
fillColor=none;strokeColor=none;
```

## Connector pattern

- Create an empty-value edge cell.
- Use `edgeStyle=orthogonalEdgeStyle`, rounded routing, a visible arrowhead, and explicit waypoints for long or branching routes.
- Put the caption in a separate transparent `relationship-caption` text cell.
- Store `data-edge-kind`, `data-color-mode`, and the resolved line colour.

## Transparent text

All standalone labels and captions must contain:

```text
strokeColor=none;fillColor=none;
```

Never use `labelBackgroundColor`. Some draw.io versions render unexpected opaque or black backgrounds from that property.

## Metadata

Add stable attributes where relevant:

- `data-kind`
- `data-resource-id`
- `data-provider`
- `data-icon-key`
- `data-icon-source`
- `data-icon-release`
- `data-edge-kind`
- `data-color-mode`
- `data-group-kind`

These attributes support validation without changing the diagram appearance.
