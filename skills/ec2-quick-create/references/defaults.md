# EC2 Quick Create Defaults

## Baseline reference
- Baseline instance (dev): `i-09f751985f7f639c4`
- AMI owner: `148623356839`
- AMI name: `GT_GCCS_StandardBuild_AML_2_on_2026-01-19_05.05.04`
- AMI id: `ami-0050647bd7efe8656`
- IAM instance profile (default): `TerraformProductionAccessRole`

## GCC current notes
- See [gcc-standard-images.md](gcc-standard-images.md) for the latest AL2 and
  AL2023 GCC base-image observations, including SSM and AWS CLI behavior.
- As of 2026-03-19, the current AL2 quick-create default should be:
  - `ami-026d0d206ed13f95c`
- As of 2026-03-19, the latest observed AL2023 GCC image is:
  - `ami-0dfac6d4e7d40dfa8`

## Fast path defaults
Use when the user says “use defaults” / “don’t ask”.
- `env=dev`
- `name=jumpbox`
- `owner_tag=unknown`
- `purpose_tag=default`
- `instance_type=t3.medium`
- `subnet_id=subnet-0d13ba2dcbb0f6d46`
- `security_group_id=sg-0c8becd22fa808f6b`
- `availability_zone=ap-southeast-1b`
- `volume_size_gb=20`
- `volume_type=gp3`
- `iops=3000`
- `throughput=125`
- `encrypted=false`
- `public_ip=false`

## Environment mapping
- `dev` account: `273828039634`
- `prod` account: `021577063369`

## Guardrails
- Private instance by default (no public IP).
- SSM access required; fail if instance is not managed by SSM.
- If `env=prod`, require explicit `subnet_id` and `security_group_id`.
- If public IP is requested, reconfirm before proceeding.
- Do not assume AWS CLI is present on the base image.
- Verify `amazon-ssm-agent` and SSM registration separately from AWS CLI.
  
## Tags added by skill
- `CreatedAt` (SGT, human readable, no spaces; e.g., `2026-01-22T14:21SGT`)
- `Repo` (git repo name if available)
- `Branch` (git branch if available)
- `ProvisionedBy=skills-ec2-quick-create`
