#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  skills/aws-ssm-run-command/scripts/ssm_get_output.sh \
    --region ap-southeast-1 \
    [--profile ihis_dev] \
    --command-id <cmd-id> \
    --instance-id i-xxx
USAGE
}

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }; }

REGION=""
PROFILE=""
COMMAND_ID=""
INSTANCE_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --command-id) COMMAND_ID="$2"; shift 2 ;;
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

need aws

[[ -n "$REGION" && -n "$COMMAND_ID" && -n "$INSTANCE_ID" ]] || {
  echo "Missing required args" >&2
  usage
  exit 1
}
[[ "$INSTANCE_ID" =~ ^i-[a-z0-9]+$ ]] || { echo "invalid instance id: $INSTANCE_ID" >&2; exit 1; }

AWS_ARGS=(--region "$REGION")
if [[ -n "$PROFILE" ]]; then
  AWS_ARGS+=(--profile "$PROFILE")
fi

aws ssm get-command-invocation \
  "${AWS_ARGS[@]}" \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  --query '{Status:Status,ResponseCode:ResponseCode,ExecutionStartDateTime:ExecutionStartDateTime,ExecutionEndDateTime:ExecutionEndDateTime,StdOut:StandardOutputContent,StdErr:StandardErrorContent}' \
  --output json
