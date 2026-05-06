#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 5 ]]; then
  echo "usage: $0 <profile> <region> <cloudos_instance_id> <gitlab_backend_instance_id> [fqdn]" >&2
  exit 2
fi

PROFILE="$1"
REGION="$2"
CLOUDOS_ID="$3"
BACKEND_ID="$4"
FQDN="${5:-gitlab.pro.synapxe.lifebit-biotech.com}"
TRACE="gitlab-trace-$(date +%Y%m%d%H%M%S)"

echo "$TRACE"

SEND_CMD="$(aws --profile "$PROFILE" --region "$REGION" ssm send-command \
  --instance-ids "$CLOUDOS_ID" \
  --document-name AWS-RunShellScript \
  --parameters "{\"commands\":[\"curl -skI --max-time 5 https://$FQDN/users/sign_in?trace=$TRACE || true\"]}" \
  --query 'Command.CommandId' --output text)"

for _ in $(seq 1 20); do
  STATUS="$(aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
    --command-id "$SEND_CMD" --instance-id "$CLOUDOS_ID" \
    --query 'Status' --output text 2>/dev/null || true)"
  if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
    break
  fi
  sleep 2
done

CHECK_CMD="$(aws --profile "$PROFILE" --region "$REGION" ssm send-command \
  --instance-ids "$BACKEND_ID" \
  --document-name AWS-RunShellScript \
  --parameters "{\"commands\":[\"docker exec gitlab-web-1 bash -lc 'grep -n --fixed-strings \\\"$TRACE\\\" /var/log/gitlab/nginx/gitlab_access.log 2>/dev/null || true'\"]}" \
  --query 'Command.CommandId' --output text)"

for _ in $(seq 1 20); do
  STATUS="$(aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
    --command-id "$CHECK_CMD" --instance-id "$BACKEND_ID" \
    --query 'Status' --output text 2>/dev/null || true)"
  if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
    break
  fi
  sleep 2
done

echo "--- trace hits on backend $BACKEND_ID ---"
aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
  --command-id "$CHECK_CMD" --instance-id "$BACKEND_ID" \
  --query 'StandardOutputContent' --output text || true
