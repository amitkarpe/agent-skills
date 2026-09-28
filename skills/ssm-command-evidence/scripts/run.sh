#!/usr/bin/env bash
set -euo pipefail

usage() {
  local exit_code="${1:-1}"
  cat <<'EOF'
Usage:
  run.sh --instance-id i-xxx --output-dir /path [--profile p] [--region r]
         [--document-name DocName --parameters-file params.json]
         [--commands-file commands.sh]

Exactly one of:
  --document-name + --parameters-file
  --commands-file
EOF
  exit "$exit_code"
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing dependency: $1" >&2
    exit 1
  }
}

need aws
need jq

INSTANCE_ID=""
OUTPUT_DIR=""
PROFILE=""
REGION=""
DOCUMENT_NAME=""
PARAMETERS_FILE=""
COMMANDS_FILE=""
WAIT_TIMEOUT=900
POLL=5

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CORE_SSM_DIR="$SKILLS_DIR/aws-ssm-run-command/scripts"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --document-name) DOCUMENT_NAME="$2"; shift 2 ;;
    --parameters-file) PARAMETERS_FILE="$2"; shift 2 ;;
    --commands-file) COMMANDS_FILE="$2"; shift 2 ;;
    --wait-timeout) WAIT_TIMEOUT="$2"; shift 2 ;;
    --poll-seconds) POLL="$2"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) usage ;;
  esac
done

[[ -z "$INSTANCE_ID" || -z "$OUTPUT_DIR" ]] && usage

if [[ -n "$COMMANDS_FILE" && -n "$DOCUMENT_NAME" ]]; then
  usage
fi
if [[ -z "$COMMANDS_FILE" && -z "$DOCUMENT_NAME" ]]; then
  usage
fi
if [[ -n "$DOCUMENT_NAME" && -z "$PARAMETERS_FILE" ]]; then
  usage
fi

mkdir -p "$OUTPUT_DIR"
LOG="$OUTPUT_DIR/run.log"
exec > >(tee -a "$LOG") 2> >(tee -a "$OUTPUT_DIR/run-errors.log" >&2)

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }

resolve_region() {
  if [[ -n "$REGION" ]]; then
    printf '%s\n' "$REGION"
    return 0
  fi
  if [[ -n "${AWS_REGION:-}" ]]; then
    printf '%s\n' "$AWS_REGION"
    return 0
  fi
  if [[ -n "${AWS_DEFAULT_REGION:-}" ]]; then
    printf '%s\n' "$AWS_DEFAULT_REGION"
    return 0
  fi
  local configured_region=""
  if [[ -n "$PROFILE" ]]; then
    configured_region="$(aws configure get region --profile "$PROFILE" 2>/dev/null || true)"
  else
    configured_region="$(aws configure get region 2>/dev/null || true)"
  fi
  [[ -n "$configured_region" ]] || {
    echo "AWS region is required via --region, AWS_REGION, AWS_DEFAULT_REGION, or aws config" >&2
    exit 1
  }
  printf '%s\n' "$configured_region"
}

save_summary_from_core() {
  local core_json="$1"
  jq -n \
    --arg instance_id "$INSTANCE_ID" \
    --arg profile "$PROFILE" \
    --arg region "$EFFECTIVE_REGION" \
    --argjson core "$core_json" \
    '{
      CommandId: $core.CommandId,
      InstanceId: $instance_id,
      DocumentName: "AWS-RunShellScript",
      Status: ($core.Output.Status // $core.Wait.Status // "Unknown"),
      StatusDetails: ($core.Wait.Status // "Unknown"),
      ResponseCode: $core.Output.ResponseCode,
      ExecutionStartDateTime: $core.Output.ExecutionStartDateTime,
      ExecutionEndDateTime: $core.Output.ExecutionEndDateTime,
      WaitMeta: ($core.Wait.WaitMeta // null),
      Profile: (if $profile == "" then null else $profile end),
      Region: $region
    }' > "$OUTPUT_DIR/summary.json"
}

AWS=(aws)
[[ -n "$PROFILE" ]] && AWS+=(--profile "$PROFILE")
EFFECTIVE_REGION="$(resolve_region)"
AWS+=(--region "$EFFECTIVE_REGION")

log "validating target instance $INSTANCE_ID"
"${AWS[@]}" ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=${INSTANCE_ID}" \
  > "$OUTPUT_DIR/instance-information.json"

PING=$(jq -r '.InstanceInformationList[0].PingStatus // empty' "$OUTPUT_DIR/instance-information.json")
[[ "$PING" == "Online" || -e "$OUTPUT_DIR/command-id.txt" ]] || {
  echo "SSM instance is not Online: ${PING:-missing}" >&2
  exit 1
}

if [[ -n "$COMMANDS_FILE" ]]; then
  [[ -f "$COMMANDS_FILE" ]] || { echo "commands file not found: $COMMANDS_FILE" >&2; exit 1; }
  if [[ -e "$OUTPUT_DIR/command-id.txt" ]]; then
    [[ ! -f "$OUTPUT_DIR/input-commands.sh" ]] || cmp -s "$COMMANDS_FILE" "$OUTPUT_DIR/input-commands.sh" || {
      echo "Prior command input differs; use its exact CommandId, not a new send" >&2
      exit 2
    }
  else
    cp "$COMMANDS_FILE" "$OUTPUT_DIR/input-commands.sh"
  fi
  DOC="AWS-RunShellScript"
  COMMENT="ssm-command-evidence $(basename "$OUTPUT_DIR")"
else
  [[ -f "$PARAMETERS_FILE" ]] || { echo "parameters file not found: $PARAMETERS_FILE" >&2; exit 1; }
  if [[ -e "$OUTPUT_DIR/command-id.txt" ]]; then
    [[ ! -f "$OUTPUT_DIR/input-parameters.json" ]] || cmp -s "$PARAMETERS_FILE" "$OUTPUT_DIR/input-parameters.json" || {
      echo "Prior document input differs; use its exact CommandId, not a new send" >&2
      exit 2
    }
  else
    cp "$PARAMETERS_FILE" "$OUTPUT_DIR/input-parameters.json"
  fi
  PARAMS_JSON="$PARAMETERS_FILE"
  DOC="$DOCUMENT_NAME"
fi

if [[ -e "$OUTPUT_DIR/command-id.txt" ]]; then
  [[ ! -f "$OUTPUT_DIR/instance-id.txt" || "$(<"$OUTPUT_DIR/instance-id.txt")" == "$INSTANCE_ID" ]] &&
  [[ ! -f "$OUTPUT_DIR/region.txt" || "$(<"$OUTPUT_DIR/region.txt")" == "$EFFECTIVE_REGION" ]] &&
  [[ ! -f "$OUTPUT_DIR/document-name.txt" || "$(<"$OUTPUT_DIR/document-name.txt")" == "$DOC" ]] || {
    echo "Prior SSM execution identity differs; stop before another send" >&2
    exit 2
  }
else
  printf '%s\n' "$INSTANCE_ID" > "$OUTPUT_DIR/instance-id.txt"
  printf '%s\n' "$EFFECTIVE_REGION" > "$OUTPUT_DIR/region.txt"
  printf '%s\n' "$DOC" > "$OUTPUT_DIR/document-name.txt"
fi

log "send or exact-ID readback document=$DOC"
if [[ -n "$COMMANDS_FILE" ]]; then
  CORE_RUN_ARGS=(
    --region "$EFFECTIVE_REGION"
    --instance-id "$INSTANCE_ID"
    --comment "$COMMENT"
    --commands-file "$COMMANDS_FILE"
    --command-id-file "$OUTPUT_DIR/command-id.txt"
    --poll-seconds "$POLL"
    --max-wait-seconds "$WAIT_TIMEOUT"
  )
  if [[ -n "$PROFILE" ]]; then
    CORE_RUN_ARGS+=(--profile "$PROFILE")
  fi

  set +e
  CORE_JSON="$("$CORE_SSM_DIR/ssm_run.sh" "${CORE_RUN_ARGS[@]}")"
  CORE_RC=$?
  set -e

  [[ -n "$CORE_JSON" ]] || CORE_JSON='{"CommandId":"","Wait":{"Status":"Unknown"},"Output":{"Status":"Unavailable","ResponseCode":null,"ExecutionStartDateTime":null,"ExecutionEndDateTime":null,"StdOut":"","StdErr":"core run produced no output"}}'

  printf '%s\n' "$CORE_JSON" > "$OUTPUT_DIR/core-run.json"
  printf '%s\n' "$DOC" > "$OUTPUT_DIR/document-name.txt"
  printf '%s\n' "$COMMENT" > "$OUTPUT_DIR/comment.txt"
  printf '%s\n' "$EFFECTIVE_REGION" > "$OUTPUT_DIR/region.txt"
  [[ -n "$PROFILE" ]] && printf '%s\n' "$PROFILE" > "$OUTPUT_DIR/profile.txt"

  if [[ "$(jq -r '.CommandId // ""' "$OUTPUT_DIR/core-run.json")" != "" ]]; then
    jq -r '.CommandId' "$OUTPUT_DIR/core-run.json" > "$OUTPUT_DIR/command-id.txt"
  fi
  jq '.Output' "$OUTPUT_DIR/core-run.json" > "$OUTPUT_DIR/invocation.json"
  jq -r '.Output.StdOut // ""' "$OUTPUT_DIR/core-run.json" > "$OUTPUT_DIR/stdout.txt"
  jq -r '.Output.StdErr // ""' "$OUTPUT_DIR/core-run.json" > "$OUTPUT_DIR/stderr.txt"
  save_summary_from_core "$CORE_JSON"

  STATUS="$(jq -r '.Output.Status // .Wait.Status // "Unknown"' "$OUTPUT_DIR/core-run.json")"
  log "command_id=$(cat "$OUTPUT_DIR/command-id.txt")"
  log "final_status=$STATUS"
  if [[ "$CORE_RC" -ne 0 || "$STATUS" != "Success" ]]; then
    exit 2
  fi
  exit 0
fi

if [[ -e "$OUTPUT_DIR/command-id.txt" ]]; then
  CMD_ID="$(<"$OUTPUT_DIR/command-id.txt")"
  [[ "$CMD_ID" =~ ^[0-9a-fA-F-]{36}$ ]] || {
    echo "Prior SSM send outcome is unknown; reconcile provider state before another send" >&2
    exit 2
  }
else
  (umask 077; set -C; printf 'PENDING\n' > "$OUTPUT_DIR/command-id.txt") || {
    echo "Could not reserve CommandId file; stop before another send" >&2
    exit 2
  }
  CMD_ID=$("${AWS[@]}" ssm send-command \
    --document-name "$DOC" \
    --instance-ids "$INSTANCE_ID" \
    --parameters "file://${PARAMS_JSON}" \
    --query 'Command.CommandId' \
    --output text)
fi

printf '%s\n' "$CMD_ID" > "$OUTPUT_DIR/command-id.txt"
printf '%s\n' "$DOC" > "$OUTPUT_DIR/document-name.txt"
printf '%s\n' "$EFFECTIVE_REGION" > "$OUTPUT_DIR/region.txt"
[[ -n "$PROFILE" ]] && printf '%s\n' "$PROFILE" > "$OUTPUT_DIR/profile.txt"
log "command_id=$CMD_ID"

WAIT_ARGS=(
  --region "$EFFECTIVE_REGION"
  --command-id "$CMD_ID"
  --instance-id "$INSTANCE_ID"
  --poll-seconds "$POLL"
  --max-wait-seconds "$WAIT_TIMEOUT"
)
if [[ -n "$PROFILE" ]]; then
  WAIT_ARGS+=(--profile "$PROFILE")
fi

set +e
WAIT_JSON="$("$CORE_SSM_DIR/ssm_wait.sh" "${WAIT_ARGS[@]}")"
WAIT_RC=$?
set -e
[[ -n "$WAIT_JSON" ]] || WAIT_JSON='{"Status":"Unknown"}'
printf '%s\n' "$WAIT_JSON" > "$OUTPUT_DIR/wait.json"

GET_ARGS=(
  --region "$EFFECTIVE_REGION"
  --command-id "$CMD_ID"
  --instance-id "$INSTANCE_ID"
)
if [[ -n "$PROFILE" ]]; then
  GET_ARGS+=(--profile "$PROFILE")
fi

set +e
OUTPUT_JSON="$("$CORE_SSM_DIR/ssm_get_output.sh" "${GET_ARGS[@]}")"
OUTPUT_RC=$?
set -e
if [[ "$OUTPUT_RC" -ne 0 || -z "$OUTPUT_JSON" ]]; then
  OUTPUT_JSON='{"Status":"Unavailable","ResponseCode":null,"ExecutionStartDateTime":null,"ExecutionEndDateTime":null,"StdOut":"","StdErr":"output fetch failed"}'
fi
printf '%s\n' "$OUTPUT_JSON" > "$OUTPUT_DIR/invocation.json"

jq -r '.StdOut // ""' "$OUTPUT_DIR/invocation.json" > "$OUTPUT_DIR/stdout.txt"
jq -r '.StdErr // ""' "$OUTPUT_DIR/invocation.json" > "$OUTPUT_DIR/stderr.txt"
jq -n \
  --arg command_id "$CMD_ID" \
  --arg instance_id "$INSTANCE_ID" \
  --arg document_name "$DOC" \
  --arg profile "$PROFILE" \
  --arg region "$EFFECTIVE_REGION" \
  --argjson wait "$WAIT_JSON" \
  --argjson output "$OUTPUT_JSON" \
  '{
    CommandId: $command_id,
    InstanceId: $instance_id,
    DocumentName: $document_name,
    Status: ($output.Status // $wait.Status // "Unknown"),
    StatusDetails: ($wait.Status // "Unknown"),
    ResponseCode: $output.ResponseCode,
    ExecutionStartDateTime: $output.ExecutionStartDateTime,
    ExecutionEndDateTime: $output.ExecutionEndDateTime,
    WaitMeta: ($wait.WaitMeta // null),
    Profile: (if $profile == "" then null else $profile end),
    Region: $region
  }' > "$OUTPUT_DIR/summary.json"

STATUS="$(jq -r '.Status // "Unknown"' "$OUTPUT_DIR/summary.json")"
log "final_status=$STATUS"
if [[ "$WAIT_RC" -ne 0 || "$STATUS" != "Success" ]]; then
  exit 2
fi
