#!/usr/bin/env bash
set -euo pipefail

valid_profile() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; }
valid_region() { [[ "$1" =~ ^[a-z]{2}(-gov)?-[a-z0-9-]+-[0-9]+$ ]]; }
valid_instance_id() { [[ "$1" =~ ^i-[0-9a-f]{8,17}$ ]]; }
valid_fqdn() {
  local fqdn="$1" label last
  [[ ${#fqdn} -le 253 && "$fqdn" == *.* && "$fqdn" != .* && "$fqdn" != *. && "$fqdn" != *..* ]] || return 1
  IFS='.' read -r -a labels <<<"$fqdn"
  for label in "${labels[@]}"; do
    [[ "$label" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$ ]] || return 1
  done
  last="${labels[${#labels[@]}-1]}"
  [[ "$last" =~ ^[A-Za-z]{2,63}$ ]]
}
parameters_json() { python3 -c 'import json,sys; print(json.dumps({"commands": [sys.argv[1]]}))' "$1"; }

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

valid_profile "$PROFILE" || { echo "invalid profile" >&2; exit 2; }
valid_region "$REGION" || { echo "invalid region" >&2; exit 2; }
valid_instance_id "$CLOUDOS_ID" || { echo "invalid CloudOS instance ID" >&2; exit 2; }
valid_instance_id "$BACKEND_ID" || { echo "invalid backend instance ID" >&2; exit 2; }
valid_fqdn "$FQDN" || { echo "invalid FQDN" >&2; exit 2; }
[[ "$TRACE" =~ ^[a-z0-9-]+$ ]] || { echo "invalid generated trace ID" >&2; exit 1; }

AWS=(aws --profile "$PROFILE" --region "$REGION")
fqdn_b64="$(printf '%s' "$FQDN" | base64 -w0)"
trace_b64="$(printf '%s' "$TRACE" | base64 -w0)"
remote_probe="fqdn=\$(printf %s '$fqdn_b64' | base64 -d); trace=\$(printf %s '$trace_b64' | base64 -d); curl -skI --max-time 5 \"https://\$fqdn/users/sign_in?trace=\$trace\" || true"
remote_check="trace=\$(printf %s '$trace_b64' | base64 -d); docker exec gitlab-web-1 bash -lc 'grep -n --fixed-strings \"\$1\" /var/log/gitlab/nginx/gitlab_access.log 2>/dev/null || true' -- \"\$trace\""

echo "$TRACE"

SEND_CMD="$("${AWS[@]}" ssm send-command \
  --instance-ids "$CLOUDOS_ID" \
  --document-name AWS-RunShellScript \
  --parameters "$(parameters_json "$remote_probe")" \
  --query 'Command.CommandId' --output text)"

for _ in $(seq 1 20); do
  STATUS="$("${AWS[@]}" ssm get-command-invocation \
    --command-id "$SEND_CMD" --instance-id "$CLOUDOS_ID" \
    --query 'Status' --output text 2>/dev/null || true)"
  if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
    break
  fi
  sleep 2
done

CHECK_CMD="$("${AWS[@]}" ssm send-command \
  --instance-ids "$BACKEND_ID" \
  --document-name AWS-RunShellScript \
  --parameters "$(parameters_json "$remote_check")" \
  --query 'Command.CommandId' --output text)"

for _ in $(seq 1 20); do
  STATUS="$("${AWS[@]}" ssm get-command-invocation \
    --command-id "$CHECK_CMD" --instance-id "$BACKEND_ID" \
    --query 'Status' --output text 2>/dev/null || true)"
  if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
    break
  fi
  sleep 2
done

echo "--- trace hits on backend $BACKEND_ID ---"
"${AWS[@]}" ssm get-command-invocation \
  --command-id "$CHECK_CMD" --instance-id "$BACKEND_ID" \
  --query 'StandardOutputContent' --output text || true
