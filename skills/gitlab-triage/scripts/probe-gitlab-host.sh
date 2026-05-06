#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "usage: $0 <profile> <region> <gitlab_instance_id> [output_dir]" >&2
  exit 2
fi

PROFILE="$1"
REGION="$2"
INSTANCE_ID="$3"
OUTDIR="${4:-$HOME/.AGENTS-temp/agent-skills/gitlab-triage/host-probe-$(date +%Y%m%d-%H%M%S)-${INSTANCE_ID}}"
mkdir -p "$OUTDIR"

CMD_ID="$(aws --profile "$PROFILE" --region "$REGION" ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name AWS-RunShellScript \
  --parameters '{"commands":["echo HOSTNAME=$(hostname)","echo --- SERVICES ---","systemctl is-active docker gitlab-runsvdir amazon-ssm-agent 2>/dev/null || true","echo --- DOCKER ---","docker ps --format \"table {{.Names}}\t{{.Status}}\t{{.Ports}}\" | awk '\''NR<=20 {print}'\'' || true","echo --- LOCAL HEALTH ---","python3 -c \"import urllib.request; urls=[\\\"http://127.0.0.1/-/health\\\",\\\"http://127.0.0.1/-/readiness\\\"];\\nfor u in urls:\\n  \\n  try:\\n    r=urllib.request.urlopen(u,timeout=5); print(u, r.status, r.read(200).decode(errors=\\\"ignore\\\"))\\n  except Exception as e:\\n    print(u, \\\"FAIL\\\", e)\" || true"]}' \
  --query 'Command.CommandId' --output text)"

for _ in $(seq 1 30); do
  STATUS="$(aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
    --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
    --query 'Status' --output text 2>/dev/null || true)"
  if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
    break
  fi
  sleep 2
done

aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
  --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" --output json > "$OUTDIR/invocation.json"

cat "$OUTDIR/invocation.json"
