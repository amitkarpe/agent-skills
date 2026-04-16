#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "usage: $0 <instance_id> <profile> <region> [output_dir]" >&2
  exit 2
fi

INSTANCE_ID="$1"
PROFILE="$2"
REGION="$3"
OUTDIR="${4:-$HOME/.AGENTS-temp/agent-skills/ecs-recovery/restart-$(date +%Y%m%d-%H%M%S)-${INSTANCE_ID}}"

mkdir -p "$OUTDIR"

send_ssm() {
  local commands_json="$1"
  aws --profile "$PROFILE" --region "$REGION" ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "$commands_json" \
    --query "Command.CommandId" \
    --output text
}

wait_and_capture() {
  local command_id="$1"
  local outfile="$2"

  for _ in $(seq 1 30); do
    status="$(aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
      --command-id "$command_id" \
      --instance-id "$INSTANCE_ID" \
      --query "Status" \
      --output text 2>/dev/null || true)"

    if [[ "$status" == "Success" || "$status" == "Failed" || "$status" == "Cancelled" || "$status" == "TimedOut" ]]; then
      break
    fi
    sleep 2
  done

  aws --profile "$PROFILE" --region "$REGION" ssm get-command-invocation \
    --command-id "$command_id" \
    --instance-id "$INSTANCE_ID" \
    --output json > "$outfile"
}

BEFORE_CMD="$(send_ssm '{"commands":["hostname","echo ---","systemctl is-active docker || true","systemctl is-active ecs || true","echo ---","iptables -t nat -S 2>/dev/null | grep -c DOCKER || echo 0"]}')"
echo "$BEFORE_CMD" > "$OUTDIR/before.cmdid"
wait_and_capture "$BEFORE_CMD" "$OUTDIR/before.json"

RESTART_CMD="$(send_ssm '{"commands":["systemctl restart docker","sleep 10","systemctl restart ecs"]}')"
echo "$RESTART_CMD" > "$OUTDIR/restart.cmdid"
wait_and_capture "$RESTART_CMD" "$OUTDIR/restart.json"

AFTER_CMD="$(send_ssm '{"commands":["hostname","echo ---","systemctl is-active docker || true","systemctl is-active ecs || true","echo ---","iptables -t nat -S 2>/dev/null | grep -c DOCKER || echo 0"]}')"
echo "$AFTER_CMD" > "$OUTDIR/after.cmdid"
wait_and_capture "$AFTER_CMD" "$OUTDIR/after.json"

python3 - <<'PY' "$OUTDIR/after.json" > "$OUTDIR/summary.txt"
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
out = data.get("StandardOutputContent", "").splitlines()
hostname = out[0] if len(out) > 0 else ""
docker = out[2] if len(out) > 2 else ""
ecs = out[3] if len(out) > 3 else ""
nat = out[5] if len(out) > 5 else ""
print(f"hostname={hostname}")
print(f"docker={docker}")
print(f"ecs={ecs}")
print(f"docker_nat_chain_count={nat}")
PY

cat "$OUTDIR/summary.txt"
