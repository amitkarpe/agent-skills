# Examples

One-shot run:

```bash
skills/aws-ssm-run-command/scripts/ssm_run.sh \
  --region ap-southeast-1 \
  --instance-id i-0123456789abcdef0 \
  --comment "ssm smoke" \
  --commands-file /path/to/commands.txt \
  --command-id-file /path/to/run/command-id.txt \
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
# Reconcile-before-repeat decision examples

| Prior state for the same authorized intent | Action |
| --- | --- |
| CommandId exists | Read back that exact ID; do not send again. |
| Execution is still running | Wait on that ID; do not send again. |
| Execution completed | Report its terminal result; a new attempt needs separate authority. |
| Send outcome unknown (`PENDING`, empty ID, or ambiguous provider state) | Stop and reconcile provider state; do not retry. |
| No prior execution after durable and provider checks | One bounded send may proceed under the owning approval. |
