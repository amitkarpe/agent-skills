# AWS Icon Policy

## Primary source

Use the latest package from:

- `https://aws.amazon.com/architecture/icons/`

AWS states that customers and partners may use these assets to create architecture diagrams and related materials. AWS also warns that third-party libraries may contain legacy icon sets and releases icon packages quarterly in Q1, Q2, and Q3.

## Source priority

1. **official-aws-package** — preferred production source. Prepare it with `scripts/prepare_aws_icons.py` and embed the selected SVG/PNG bytes in the `.drawio` file. A manually downloaded ZIP must use the explicit `--official-local-package` provenance assertion.
2. **drawio-native-aws4** — accepted fallback when the official package cannot be prepared or the user specifically wants native draw.io shapes. Record that it is draw.io-bundled and may not be the latest AWS release.
3. **verified AWS Labs derivative** — acceptable only when its release is recorded and the direct package is unavailable.
4. **bundled fallback PNG** — regression tests only. Never silently use it in a production diagram.
5. Generic cloud icons or unofficial AWS lookalikes — prohibited for AWS services.

## Selection rules

- Prefer architecture service icons for service-level diagrams.
- Use resource icons only when the resource subtype matters.
- Use category icons only for deliberately high-level views.
- Keep one icon generation/source within a diagram whenever possible.
- Embed official image bytes; never rely on remote URLs or local file paths.
- Record source, release, canonical key, original file, and hash in metadata.

## Native draw.io mapping

For native mode, use a tested mapping from canonical keys to `mxgraph.aws4` resource names. Most entries use the `resourceIcon` wrapper. Shapes that draw.io exposes only as direct AWS4 shapes belong in the map's `direct_shapes` object. Do not guess an unsupported native name. If the mapping is unavailable:

- use the official embedded icon cache; or
- use a neutral labelled card and report the missing mapping.

Search `assets/aws4-shapes.json` with `scripts/search_aws4_shapes.py` before
using MCP. The bundled registry is derived from the AWS-owned
`awslabs/agent-plugins` diagram skill and records its draw.io source/version.
It is licensed under Apache-2.0; the corresponding license and notice are
stored beside the registry. A registry match proves the name exists in that
catalog, but exact local Desktop rendering is still required because draw.io
versions can differ.

Record newly accepted native mappings in `assets/native-aws4-map.json` under
`verification`, including the registry version, exact draw.io Desktop version,
verification date, and result. Do not add a candidate that renders as a blank,
generic block, ambiguous icon, or otherwise degraded shape. Keep rejected
candidate evidence in the run result rather than in the stable mapping table.

## Refresh policy

Refresh the official icon cache when:

- AWS publishes a new quarterly package;
- a requested service is missing;
- a diagram mixes legacy and current icon generations;
- the user requests the latest icons explicitly.
