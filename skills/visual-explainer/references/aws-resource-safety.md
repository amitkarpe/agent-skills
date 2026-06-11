# AWS Resource Safety

## Sensitive values

Mask or omit by default:

- Access keys, secret keys, tokens, cookies, private keys.
- 12-digit AWS account IDs unless the user approves keeping them.
- Public IPs, internal IPs, hostnames, ARNs, and resource IDs if copied from sensitive environments.

## Unknown resources

Never invent realistic values. Use:

- `unknown / needs refresh`
- `example only`
- `placeholder`

## Useful AWS visual mappings

- AMI → launch template → EC2 instance.
- AMI → EBS snapshot → KMS key.
- DEV account → AMI share → PROD account.
- Pipeline → hardening → scan → promote → deploy → cleanup.
