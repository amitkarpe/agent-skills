# Discovery-first diagrams

Use this path when you have read access to the real estate. A hand-written spec
shows what the agent remembered; a discovery-first spec shows what is deployed,
and a coverage gate proves nothing was dropped or invented.

## 1. Collect (read only)

Run one per account or stack. Keep the output outside Git, for example under
`~/.AGENTS-temp/<repo>/discovery/`: it holds resource IDs.

AWS Config (best: it covers every recorded type and gives relationships):

```bash
aws configservice select-resource-config --output json \
  --expression "SELECT resourceId, resourceType, resourceName, tags, relationships" \
  > config-dev.json
```

Follow `NextToken` and save the pages as a JSON list when the account is large.
For many accounts, use `select-aggregate-resource-config` with the aggregator name.
Config only sees resource types it records: say so in the diagram footer when
recording is partial.

Terraform (the managed resources of one state):

```bash
terraform show -json > terraform-dev.json
```

## 2. Normalize

```bash
scripts/python.sh scripts/discover_normalize.py \
  --input config DEV config-dev.json \
  --input terraform DEV terraform-dev.json \
  --output discovery.json
```

`GROUP` (here `DEV`) is the display label for the account or environment. Keys
look like `DEV/AWS::S3::Bucket/<id>` or `DEV/<terraform address>`. Data sources
are skipped: they are lookups, not deployed resources.

## 3. Draft the spec

```bash
scripts/python.sh scripts/discovery_to_spec.py discovery.json SPEC.json --title "..."
```

- Each resource type maps through `assets/discovery-type-map.json` to a tier
  band and an icon (`role: show`) or to a fold reason (`fold`). Folded resources
  (IAM attachments, security group rules, bucket policies, subnets) go to
  `coverage.omitted` with that reason. They are listed, not lost.
- Three or more of one kind in one group become one card, "N × S3 buckets".
  Above 16 cards the threshold drops to two.
- Labels are cleaned: ARNs, 12-digit numbers, instance-style IDs and IPv4
  addresses are replaced. Check names yourself before sharing.
- Unmapped types are drawn as label-only cards in an "Unmapped types" band and
  reported. Add them to the type map, or fold them with a reason.
- No arrows are drawn. Discovered relations ("is associated with", "depends
  on") are listed in `coverage.relation_hints`. Turn the ones that carry a real
  flow into edges with a caption and waypoints.

## 4. Edit, keeping coverage true

Rename, merge, move or split cards freely, but keep every key in exactly one
node `covers` list or in `coverage.omitted` with a reason. To drop a card,
move its keys to `omitted` and say why ("out of scope: shared networking
account").

## 5. Build and finalize

Pass `--discovery discovery.json` to both review passes:

```bash
scripts/python.sh scripts/build_and_review.py SPEC.json OUT --name architecture --pass-number 1 \
  --discovery discovery.json
```

The build runs `check_coverage.py` first and stops on any of these:
- a discovered resource that is neither drawn nor omitted;
- a `covers` or `omitted` key that discovery does not contain (invented);
- a resource drawn twice, or both drawn and omitted;
- an omit without a reason;
- a discovery file that changed since the draft (`discovery_sha256`).

A spec with a `coverage` block cannot be built without `--discovery`.
`finalize_diagram.py` refuses a pass 2 whose coverage is not PASS, and writes
the counts into the review summary.

## Limits

- The draft is a layout of what exists, grouped by tier. It is not the story.
  Flows, the primary message and the split into overview and detail views stay
  the agent's work, through the normal two-pass review.
- Coverage proves completeness against the discovery file, not against AWS.
  Partial Config recording or a partial Terraform state gives a partial picture.
- The preview renderer draws placeholder circles for native icons. Use draw.io
  Desktop for the exact export.
