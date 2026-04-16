#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: $0 <profile> <region> <since_timestamp> <instance_id> [instance_id...]" >&2
  exit 2
fi

PROFILE="$1"
REGION="$2"
SINCE_TS="$3"
shift 3

for INSTANCE in "$@"; do
  echo "=== $INSTANCE ==="
  CMD_ID="$(aws --profile "$PROFILE" --region "$REGION" ssm send-command \
    --document-name "AWS-RunShellScript" \
    --instance-ids "$INSTANCE" \
    --parameters "{\"commands\":[\"hostname\",\"echo ---\",\"journalctl -u docker --since \\\"$SINCE_TS\\\" --no-pager 2>/dev/null | grep -E \\\"awslogs|failed to create Cloudwatch log stream|failed to refresh cached credentials|failed to load credentials|retry quota exceeded\\\" | tail -50 || true\"]}" \
    --query 'Command.CommandId' \
    --output text)"

  for _ in $(seq 1 30); do
    STATUS="$(aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
      --command-id "$CMD_ID" \
      --instance-id "$INSTANCE" \
      --query 'Status' \
      --output text 2>/dev/null || true)"
    if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
      break
    fi
    sleep 2
  done

  aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$INSTANCE" \
    --query 'StandardOutputContent' \
    --output text || true
done
