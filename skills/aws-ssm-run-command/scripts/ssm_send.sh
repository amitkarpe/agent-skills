#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  skills/aws-ssm-run-command/scripts/ssm_send.sh \
    --region ap-southeast-1 \
    [--profile ihis_dev] \
    [--dry-run] \
    --instance-ids i-aaa,i-bbb \
    --comment "text" \
    --commands-file /path/to/commands.txt \
    --execution-timeout-seconds 1800
USAGE
}

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }; }

REGION=""
PROFILE=""
INSTANCE_IDS_CSV=""
COMMENT=""
COMMANDS_FILE=""
EXEC_TIMEOUT=""
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --instance-ids) INSTANCE_IDS_CSV="$2"; shift 2 ;;
    --comment) COMMENT="$2"; shift 2 ;;
    --commands-file) COMMANDS_FILE="$2"; shift 2 ;;
    --execution-timeout-seconds) EXEC_TIMEOUT="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

need aws
need jq

[[ -n "$REGION" && -n "$INSTANCE_IDS_CSV" && -n "$COMMENT" && -n "$COMMANDS_FILE" && -n "$EXEC_TIMEOUT" ]] || {
  echo "Missing required args" >&2
  usage
  exit 1
}
[[ -f "$COMMANDS_FILE" ]] || { echo "commands file not found: $COMMANDS_FILE" >&2; exit 1; }
[[ "$EXEC_TIMEOUT" =~ ^[0-9]+$ ]] || { echo "execution timeout must be integer seconds" >&2; exit 1; }

mapfile -t COMMANDS < "$COMMANDS_FILE"
for idx in "${!COMMANDS[@]}"; do
  COMMANDS[$idx]="${COMMANDS[$idx]%$'\r'}"
done
[[ ${#COMMANDS[@]} -gt 0 ]] || { echo "commands file is empty" >&2; exit 1; }
has_non_empty_command="false"
for line in "${COMMANDS[@]}"; do
  if [[ "$line" =~ [^[:space:]] ]]; then
    has_non_empty_command="true"
    break
  fi
done
[[ "$has_non_empty_command" == "true" ]] || { echo "commands file is empty" >&2; exit 1; }

IFS=',' read -r -a RAW_INSTANCE_IDS <<< "$INSTANCE_IDS_CSV"
INSTANCE_IDS=()
for raw in "${RAW_INSTANCE_IDS[@]}"; do
  id="${raw//[[:space:]]/}"
  [[ -n "$id" ]] || continue
  [[ "$id" =~ ^i-[a-z0-9]+$ ]] || { echo "invalid instance id: $id" >&2; exit 1; }
  INSTANCE_IDS+=("$id")
done
[[ ${#INSTANCE_IDS[@]} -gt 0 ]] || { echo "no instance ids provided" >&2; exit 1; }

AWS_ARGS=(--region "$REGION")
if [[ -n "$PROFILE" ]]; then
  AWS_ARGS+=(--profile "$PROFILE")
fi

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

jq -n \
  --arg timeout "$EXEC_TIMEOUT" \
  --argjson commands "$(printf '%s\n' "${COMMANDS[@]}" | jq -R . | jq -s .)" \
  '{commands: $commands, executionTimeout: [$timeout]}' > "$payload_file"

if [[ "$DRY_RUN" == "true" ]]; then
  jq -n -c \
    --arg region "$REGION" \
    --arg profile "$PROFILE" \
    --arg comment "$COMMENT" \
    --argjson timeout "$EXEC_TIMEOUT" \
    --argjson instance_ids "$(printf '%s\n' "${INSTANCE_IDS[@]}" | jq -R . | jq -s .)" \
    --argjson parameters "$(cat "$payload_file")" \
    '{
      DryRun: true,
      Region: $region,
      Profile: (if $profile == "" then null else $profile end),
      DocumentName: "AWS-RunShellScript",
      InstanceIds: $instance_ids,
      Comment: $comment,
      ExecutionTimeoutSeconds: $timeout,
      Parameters: $parameters
    }'
  exit 0
fi

aws sts get-caller-identity "${AWS_ARGS[@]}" --output json >/dev/null

aws ssm send-command \
  "${AWS_ARGS[@]}" \
  --document-name AWS-RunShellScript \
  --comment "$COMMENT" \
  --instance-ids "${INSTANCE_IDS[@]}" \
  --timeout-seconds "$EXEC_TIMEOUT" \
  --parameters "file://$payload_file" \
  --query 'Command.CommandId' \
  --output text
