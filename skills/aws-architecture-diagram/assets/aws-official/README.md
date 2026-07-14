# Official AWS Icon Cache

The complete AWS icon package is not bundled because AWS refreshes it regularly and the archive is large.

## Online preparation

```bash
python3 scripts/prepare_aws_icons.py --output assets/aws-official/current
```

The script discovers the current package only from the official AWS Architecture Icons page and downloads only from AWS-owned hosts.

## Offline preparation

Download the ZIP manually from `https://aws.amazon.com/architecture/icons/`, then run:

```bash
python3 scripts/prepare_aws_icons.py \
  --package-zip /path/to/Icon-package_DATE.zip \
  --official-local-package \
  --output assets/aws-official/current
```

`--official-local-package` is an explicit provenance assertion. Without it, a local ZIP is catalogued as unverified and cannot satisfy official-icon validation.

The generated `catalog.json` records the package hash, release filename, verification method, icon paths, and per-icon hashes.
