#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  skills/aws-ssm-run-command/scripts/ssm_run.sh \
    --region ap-southeast-1 \
    [--profile ihis_dev] \
    --instance-id i-xxx \
    --comment "text" \
    --commands-file /path/to/commands.txt \
    [--job short|long] \
    [--execution-timeout-seconds N] \
    [--poll-seconds N] \
    [--max-wait-seconds N] \
    [--retry-initial-errors-seconds N]

Defaults:
  --job short => poll 10, exec-timeout 1800
  --job long  => poll 300, exec-timeout 10800
  --max-wait-seconds 0 (wait indefinitely)
  --retry-initial-errors-seconds 60
USAGE
}

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }; }

REGION=""
PROFILE=""
INSTANCE_ID=""
COMMENT=""
COMMANDS_FILE=""
JOB="short"
EXEC_TIMEOUT=""
POLL_SECONDS=""
MAX_WAIT_SECONDS="0"
RETRY_INITIAL_ERRORS_SECONDS="60"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    --comment) COMMENT="$2"; shift 2 ;;
    --commands-file) COMMANDS_FILE="$2"; shift 2 ;;
    --job) JOB="$2"; shift 2 ;;
    --execution-timeout-seconds) EXEC_TIMEOUT="$2"; shift 2 ;;
    --poll-seconds) POLL_SECONDS="$2"; shift 2 ;;
    --max-wait-seconds) MAX_WAIT_SECONDS="$2"; shift 2 ;;
    --retry-initial-errors-seconds) RETRY_INITIAL_ERRORS_SECONDS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

need jq

[[ -n "$REGION" && -n "$INSTANCE_ID" && -n "$COMMENT" && -n "$COMMANDS_FILE" ]] || {
  echo "Missing required args" >&2
  usage
  exit 1
}
[[ -f "$COMMANDS_FILE" ]] || { echo "commands file not found: $COMMANDS_FILE" >&2; exit 1; }
[[ "$INSTANCE_ID" =~ ^i-[a-z0-9]+$ ]] || { echo "invalid instance id: $INSTANCE_ID" >&2; exit 1; }

case "$JOB" in
  short)
    : "${EXEC_TIMEOUT:=1800}"
    : "${POLL_SECONDS:=10}"
    ;;
  long)
    : "${EXEC_TIMEOUT:=10800}"
    : "${POLL_SECONDS:=300}"
    ;;
  *)
    echo "job must be short or long" >&2
    exit 1
    ;;
esac

[[ "$EXEC_TIMEOUT" =~ ^[0-9]+$ ]] || { echo "execution-timeout-seconds must be integer" >&2; exit 1; }
[[ "$POLL_SECONDS" =~ ^[0-9]+$ ]] || { echo "poll-seconds must be integer" >&2; exit 1; }
[[ "$MAX_WAIT_SECONDS" =~ ^[0-9]+$ ]] || { echo "max-wait-seconds must be integer" >&2; exit 1; }
[[ "$RETRY_INITIAL_ERRORS_SECONDS" =~ ^[0-9]+$ ]] || { echo "retry-initial-errors-seconds must be integer" >&2; exit 1; }

base_dir="$(cd "$(dirname "$0")" && pwd)"

send_args=(
  --region "$REGION"
  --instance-ids "$INSTANCE_ID"
  --comment "$COMMENT"
  --commands-file "$COMMANDS_FILE"
  --execution-timeout-seconds "$EXEC_TIMEOUT"
)
if [[ -n "$PROFILE" ]]; then
  send_args+=(--profile "$PROFILE")
fi

command_id="$($base_dir/ssm_send.sh "${send_args[@]}")"

echo "SSM_COMMAND_ID=$command_id" >&2

wait_args=(
  --region "$REGION"
  --command-id "$command_id"
  --instance-id "$INSTANCE_ID"
  --poll-seconds "$POLL_SECONDS"
  --max-wait-seconds "$MAX_WAIT_SECONDS"
  --retry-initial-errors-seconds "$RETRY_INITIAL_ERRORS_SECONDS"
)
if [[ -n "$PROFILE" ]]; then
  wait_args+=(--profile "$PROFILE")
fi

set +e
wait_json="$($base_dir/ssm_wait.sh "${wait_args[@]}")"
wait_rc=$?
set -e

if [[ -z "$wait_json" ]]; then
  wait_json='{"Status":"Unknown"}'
fi

get_args=(
  --region "$REGION"
  --command-id "$command_id"
  --instance-id "$INSTANCE_ID"
)
if [[ -n "$PROFILE" ]]; then
  get_args+=(--profile "$PROFILE")
fi

set +e
output_json="$($base_dir/ssm_get_output.sh "${get_args[@]}")"
output_rc=$?
set -e

if [[ "$output_rc" -ne 0 || -z "$output_json" ]]; then
  output_json='{"Status":"Unavailable","ResponseCode":null,"ExecutionStartDateTime":null,"ExecutionEndDateTime":null,"StdOut":"","StdErr":"output fetch failed"}'
fi

jq -n -c \
  --arg command_id "$command_id" \
  --argjson wait "$wait_json" \
  --argjson output "$output_json" \
  '{CommandId:$command_id,Wait:$wait,Output:$output}'

status="$(printf '%s' "$wait_json" | jq -r '.Status // "Unknown"')"
if [[ "$wait_rc" -ne 0 ]]; then
  exit "$wait_rc"
fi
if [[ "$status" != "Success" ]]; then
  exit 1
fi
