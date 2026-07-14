# AWS Diagram Visual Design System

## Canvas and hierarchy

- Default canvas: 1920 × 1080, light neutral background, 48–64px outer margin.
- Title: 28–32px; subtitle: 15–17px.
- Boundary title: 17–20px; subnet title: 15–17px.
- Service label: 15–17px; connector caption: 12–14px; footer: 10–12px.
- Use an 8px or 10px layout grid.
- Keep at least 28px between service nodes, 40px between stages, and 20px between content and a container border.

## Colour palette

Use colour sparingly and consistently.

| Meaning | Border / accent | Light fill |
|---|---|---|
| AWS/VPC scope | `#2E7D32` | `#F7FBF7` |
| Public subnet / web tier | `#2E7D32` | `#F0F8F1` |
| Private application tier | `#2563EB` | `#EFF6FF` |
| Private database tier | `#6D28D9` | `#F5F3FF` |
| Compute / scaling emphasis | `#E8790C` | `#FFF7ED` |
| Observability | `#C2185B` | `#FDF2F8` |
| Neutral external system | `#64748B` | `#F8FAFC` |
| AWS title accent | `#FF9900` | n/a |

Do not create a different card colour for every service. Use tier or responsibility colours.

## Boundaries

- Draw boundaries as empty shells with separate transparent title cells.
- VPC: solid 2px border with a very light fill.
- Availability Zone: blue dashed 2px border and transparent or near-white fill.
- Subnet: 1.5–2px solid tier-coloured border and a light matching fill.
- Keep titles in a protected top band; do not route connectors through boundary titles.
- Give the outer boundary title at least 24px left/top inset and at least 8px
  clearance from every shell border. Use a fixed 16-20px corner radius for the
  outer boundary instead of a percentage-like radius.

## Service nodes

Use one of these variants:

1. `icon-above`: best inside subnets and for edge services. Icon centred above a two-line label.
2. `icon-left`: best for process flows and detailed service cards.
3. `label-only`: only for actors, notes, or neutral systems without an approved icon.

A service node is composed of separate cells:

- endpoint/card cell;
- icon cell;
- transparent label cell.

For `icon-above`, default to 140–170px width and 96–116px height. Keep one icon size across a diagram, normally 52–60px.

## Connectors

- Use orthogonal routing and 2.5–3px strokes for primary flows.
- Use 2–2.5px dashed strokes for supporting, control, observability, replication, or planned flows.
- Use `block` arrowheads with consistent size.
- Default connector colour mode: `source`.
- Put captions in whitespace beside or above the line. A caption must clear its
  own connector by at least 1px and must never sit on an icon, label, card, or
  boundary title.
- Exempt only the connector endpoint where it leaves or enters its declared
  resource-card border; source and target icons or labels remain protected.
- Use explicit waypoints for fan-out, long cross-zone, and external-service routes.
- Prefer one clean bus and short branches over several parallel overlapping edges.

## Text

- Use separate text cells with `fillColor=none` and `strokeColor=none`.
- Never use `labelBackgroundColor`.
- Prefer service name on line 1 and purpose on line 2.
- Avoid labels longer than 42 characters per line.
- Increase the card or split the view instead of reducing service text below 15px.

## Legend

Add a legend when the diagram uses multiple subnet colours, multiple connector styles, or state markings. A legend should explain only non-obvious conventions. Keep it in unused outer whitespace and separate it from the main flow.
