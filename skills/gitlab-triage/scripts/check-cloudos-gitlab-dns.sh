#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: $0 <profile> <region> <target_fqdn> <instance_id> [instance_id...]" >&2
  exit 2
fi

PROFILE="$1"
REGION="$2"
TARGET="$3"
shift 3

for INSTANCE in "$@"; do
  echo "=== $INSTANCE ==="
  CMD_ID="$(aws --profile "$PROFILE" --region "$REGION" ssm send-command \
    --document-name AWS-RunShellScript \
    --instance-ids "$INSTANCE" \
    --parameters "{\"commands\":[\"echo HOSTNAME=\\$(hostname)\",\"echo TARGET=$TARGET\",\"echo --- GETENT ---\",\"getent hosts $TARGET || true\",\"echo --- NSLOOKUP ---\",\"nslookup $TARGET 2>/dev/null || true\",\"echo --- HTTPS ---\",\"curl -skI --max-time 5 https://$TARGET || true\"]}" \
    --query 'Command.CommandId' --output text)"
  for _ in $(seq 1 30); do
    STATUS="$(aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
      --command-id "$CMD_ID" --instance-id "$INSTANCE" \
      --query 'Status' --output text 2>/dev/null || true)"
    if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
      break
    fi
    sleep 2
  done
  aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
    --command-id "$CMD_ID" --instance-id "$INSTANCE" \
    --query 'StandardOutputContent' --output text || true
done
