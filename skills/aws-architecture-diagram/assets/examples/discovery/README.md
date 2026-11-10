# Discovery examples

- `config-select.example.json`, `terraform-show.example.json`: synthetic inputs for `self_test.sh`. The IDs are fake.
- `ami-factory-dev.*`: the reference result. It is the AMI Factory in the DEV account, drafted from real read-only
  AWS Config discovery (977 resources, 10 Nov 2026), then edited by the agent:
  - cards renamed by purpose;
  - ten numbered flows from aws-factory `SPEC.md`;
  - four grey cards for what Config does not record;
  - official AWS icons, exported with draw.io Desktop 32.6.10.

  The spec holds only hashed discovery keys. The discovery file stays private, so `check_coverage.py` cannot be
  re-run from this folder. Use these files as the quality bar for layout, icons, captions and legend.
