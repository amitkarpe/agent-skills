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

if [[ $# -lt 4 ]]; then
  echo "usage: $0 <profile> <region> <target_fqdn> <instance_id> [instance_id...]" >&2
  exit 2
fi

PROFILE="$1"
REGION="$2"
TARGET="$3"
shift 3

valid_profile "$PROFILE" || { echo "invalid profile" >&2; exit 2; }
valid_region "$REGION" || { echo "invalid region" >&2; exit 2; }
valid_fqdn "$TARGET" || { echo "invalid FQDN" >&2; exit 2; }
AWS=(aws --profile "$PROFILE" --region "$REGION")
target_b64="$(printf '%s' "$TARGET" | base64 -w0)"
remote_command="target=\$(printf %s '$target_b64' | base64 -d); echo HOSTNAME=\$(hostname); echo \"TARGET=\$target\"; echo --- GETENT ---; getent hosts \"\$target\" || true; echo --- NSLOOKUP ---; nslookup \"\$target\" 2>/dev/null || true; echo --- HTTPS ---; curl -skI --max-time 5 \"https://\$target\" || true"

for INSTANCE in "$@"; do
  valid_instance_id "$INSTANCE" || { echo "invalid instance ID" >&2; exit 2; }
  echo "=== $INSTANCE ==="
  CMD_ID="$("${AWS[@]}" ssm send-command \
    --document-name AWS-RunShellScript \
    --instance-ids "$INSTANCE" \
    --parameters "$(parameters_json "$remote_command")" \
    --query 'Command.CommandId' --output text)"
  for _ in $(seq 1 30); do
    STATUS="$("${AWS[@]}" ssm get-command-invocation \
      --command-id "$CMD_ID" --instance-id "$INSTANCE" \
      --query 'Status' --output text 2>/dev/null || true)"
    if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" || "$STATUS" == "TimedOut" ]]; then
      break
    fi
    sleep 2
  done
  "${AWS[@]}" ssm get-command-invocation \
    --command-id "$CMD_ID" --instance-id "$INSTANCE" \
    --query 'StandardOutputContent' --output text || true
done
