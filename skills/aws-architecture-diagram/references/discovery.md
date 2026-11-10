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
When the only access path is a CI job with a log size limit, keep only the
fields above (Name tag, relationship type, ID and name), sort, gzip and base64
the result, print it in numbered chunks with its checksum, and reassemble
locally. Never print credentials or presigned URLs.
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
scripts/python.sh scripts/discovery_to_spec.py discovery.json SPEC.json --title "..." \
  --scope 'ami-factory|aws-factory' --scope-reason "another project or the shared landing zone"
```

- **Scope first.** A real account holds other projects and the landing zone.
  `--scope` is a case-insensitive regex on name or key; everything else goes to
  `coverage.omitted` as "out of scope: <reason>", so it is still accounted for.
  `--scope-follow` also pulls in directly related resources; it is off by
  default because shared subnets and security groups pull in other projects.
- Each resource type maps through `assets/discovery-type-map.json` to a tier
  band and an icon (`role: show`) or to a fold reason (`fold`). Folded resources
  (IAM attachments, security group rules, Image Builder recipes, subnets) go to
  `coverage.omitted` with that reason. They are listed, not lost.
- `name_folds` in the type map fold AWS-managed and landing-zone resources by
  name (service-linked roles, `alias/aws/*`, `CodeDeployDefault.*`, ...), and
  the `platform` fold covers account-baseline types (Config compliance records,
  CloudFormation stack sets, account public access block).
- Each resource gets its own card. Only when the draft exceeds `--max-cards`
  (default 16) are the largest kinds merged into "N × S3 buckets" cards, the
  largest first.
- Labels and cell IDs are cleaned: ARNs, 12-digit numbers, instance-style IDs
  and IPv4 addresses are replaced. Rename cards to plain purpose names
  ("S3 bucket / release evidence") in the edit step.
- The spec never holds raw resource keys: `covers` and `omitted` store
  `k:` + the first 16 hex of the key's SHA-256. The raw keys stay in the private
  discovery file, so the spec and `.drawio` can be shared.
- Unmapped types are drawn as label-only cards in an "Unmapped types" band and
  reported. Add them to the type map, or fold them with a reason.
- No arrows are drawn. Discovered relations ("is associated with", "depends
  on") are listed in `coverage.relation_hints`. Turn the ones that carry a real
  flow into edges with a caption, anchors and waypoints, from the owning repo's
  own description of the flow.

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
- Config does not record every type (for example SSM parameters in some
  accounts). A resource the flow needs but discovery lacks can be added as a
  node without `covers`; say in the footer that it is not from discovery.
- The review does not measure legend items: check that the last legend line
  sits inside its box (about 56 px + 32 px per item).
