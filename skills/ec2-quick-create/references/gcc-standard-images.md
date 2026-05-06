# GCC Standard Images Notes

This note records the current behavior of the GCC standard base images used by
HCR and quick EC2 creation.

Verified on 2026-03-19 from disposable DEV probes.

## Current base images

- AL2:
  - owner: `148623356839`
  - name: `GT_GCCS_StandardBuild_AML_2_on_2026-03-19_05.05.57`
  - image id: `ami-026d0d206ed13f95c`
- AL2023:
  - owner: `148623356839`
  - name: `GT_GCCS_StandardBuild_AL2023_2_on_2026-03-19_05.09.37`
  - image id: `ami-0dfac6d4e7d40dfa8`

## What the probes showed

### AL2 probe

The disposable AL2 instance booted with:

- `amazon-ssm-agent` installed and enabled
- `amazon-ssm-agent` started during boot
- `awscli` installed at `/usr/bin/aws`

The same host did **not** appear in `aws ssm describe-instance-information`
within the short boot window used for the probe.

### AL2023 probe

The disposable AL2023 instance booted with:

- `amazon-ssm-agent` installed and enabled
- `amazon-ssm-agent` started during boot
- `awscli` **not** installed

The same host did **not** appear in `aws ssm describe-instance-information`
within the short boot window used for the probe.

## Practical takeaways

- Do **not** assume AWS CLI is shipped on GCC images.
- Do **not** assume SSM registration is immediate after launch, even when the
  agent is installed and starts.
- Treat the raw GCC images as bootstrap bases, not as finished operational
  hosts.

## Recommended pattern

For a long-lived "next 3 months" host family, prefer a derived AMI that is:

1. launched from the GCC base image
2. verified for `amazon-ssm-agent`
3. optionally bootstrapped with `awscli` if your workflow needs it
4. tested for SSM visibility in the target VPC/subnet
5. documented as the approved baseline for reuse

## Installing AWS CLI without SSM

Yes, it is possible to install AWS CLI without SSM.

Practical options:

- `user-data` / cloud-init on first boot
- AMI bake step
- SSH or console access
- `yum`/`dnf` install from package repos or a mirrored RPM source

The key dependency is not SSM. The key dependency is a working boot-time
execution path and package source access.

## Verification commands

On a disposable instance:

```bash
rpm -q amazon-ssm-agent awscli
systemctl is-enabled amazon-ssm-agent
systemctl status amazon-ssm-agent --no-pager
aws ssm describe-instance-information --region ap-southeast-1
```

If `awscli` is missing and you still want it, install it via `yum`/`dnf` or
your standard bootstrap path. If SSM is missing, fix the agent/bootstrap path
first.
