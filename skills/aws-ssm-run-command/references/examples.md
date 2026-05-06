# Examples

One-shot run:

```bash
skills/aws-ssm-run-command/scripts/ssm_run.sh \
  --region ap-southeast-1 \
  --instance-id i-0123456789abcdef0 \
  --comment "ssm smoke" \
  --commands-file /path/to/commands.txt \
  --job short
```

Dry-run payload preview:

```bash
skills/aws-ssm-run-command/scripts/ssm_send.sh \
  --region ap-southeast-1 \
  --instance-ids i-0123456789abcdef0 \
  --comment "preview only" \
  --commands-file /path/to/commands.txt \
  --execution-timeout-seconds 1800 \
  --dry-run
```
