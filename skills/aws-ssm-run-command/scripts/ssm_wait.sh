#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  skills/aws-ssm-run-command/scripts/ssm_wait.sh \
    --region ap-southeast-1 \
    [--profile ihis_dev] \
    --command-id <cmd-id> \
    --instance-id i-xxx \
    [--poll-seconds 10] \
    [--max-wait-seconds 0] \
    [--retry-initial-errors-seconds 60]

Notes:
  --max-wait-seconds 0 means wait indefinitely.
USAGE
}

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }; }

emit_timeout() {
  local elapsed="$1"
  jq -n -c \
    --argjson elapsed "$elapsed" \
    --argjson poll "$POLL_SECONDS" \
    '{Status:"TimedOut",WaitMeta:{ElapsedSeconds:$elapsed,PollSeconds:$poll}}'
  exit 2
}

REGION=""
PROFILE=""
COMMAND_ID=""
INSTANCE_ID=""
POLL_SECONDS="10"
MAX_WAIT_SECONDS="0"
RETRY_INITIAL_ERRORS_SECONDS="60"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --command-id) COMMAND_ID="$2"; shift 2 ;;
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    --poll-seconds) POLL_SECONDS="$2"; shift 2 ;;
    --max-wait-seconds) MAX_WAIT_SECONDS="$2"; shift 2 ;;
    --retry-initial-errors-seconds) RETRY_INITIAL_ERRORS_SECONDS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

need aws
need jq

[[ -n "$REGION" && -n "$COMMAND_ID" && -n "$INSTANCE_ID" ]] || {
  echo "Missing required args" >&2
  usage
  exit 1
}
[[ "$POLL_SECONDS" =~ ^[0-9]+$ ]] || { echo "poll seconds must be integer" >&2; exit 1; }
[[ "$MAX_WAIT_SECONDS" =~ ^[0-9]+$ ]] || { echo "max wait seconds must be integer" >&2; exit 1; }
[[ "$RETRY_INITIAL_ERRORS_SECONDS" =~ ^[0-9]+$ ]] || { echo "retry-initial-errors-seconds must be integer" >&2; exit 1; }
[[ "$INSTANCE_ID" =~ ^i-[a-z0-9]+$ ]] || { echo "invalid instance id: $INSTANCE_ID" >&2; exit 1; }

AWS_ARGS=(--region "$REGION")
if [[ -n "$PROFILE" ]]; then
  AWS_ARGS+=(--profile "$PROFILE")
fi

start_epoch=$(date +%s)

while true; do
  now_epoch=$(date +%s)
  elapsed=$((now_epoch - start_epoch))

  stderr_file="$(mktemp)"
  set +e
  result_json=$(aws ssm get-command-invocation \
    "${AWS_ARGS[@]}" \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --query '{Status:Status,ResponseCode:ResponseCode,ExecutionStartDateTime:ExecutionStartDateTime,ExecutionEndDateTime:ExecutionEndDateTime}' \
    --output json 2>"$stderr_file")
  aws_rc=$?
  set -e

  if [[ "$aws_rc" -eq 0 ]]; then
    rm -f "$stderr_file"
    status="$(printf '%s' "$result_json" | jq -r '.Status')"
    case "$status" in
      Success|Cancelled|TimedOut|Failed)
        printf '%s' "$result_json" | jq -c \
          --argjson elapsed "$elapsed" \
          --argjson poll "$POLL_SECONDS" \
          '. + {WaitMeta:{ElapsedSeconds:$elapsed,PollSeconds:$poll}}'
        exit 0
        ;;
    esac
  else
    err_text="$(cat "$stderr_file")"
    rm -f "$stderr_file"

    if [[ "$elapsed" -le "$RETRY_INITIAL_ERRORS_SECONDS" ]] && grep -Eq 'InvocationDoesNotExist|ThrottlingException|InternalServerError' <<<"$err_text"; then
      now_epoch=$(date +%s)
      elapsed=$((now_epoch - start_epoch))

      if [[ "$MAX_WAIT_SECONDS" -gt 0 ]]; then
        if [[ "$elapsed" -ge "$MAX_WAIT_SECONDS" ]]; then
          emit_timeout "$elapsed"
        fi

        remaining=$((MAX_WAIT_SECONDS - elapsed))
        sleep_seconds="$POLL_SECONDS"
        if [[ "$remaining" -lt "$sleep_seconds" ]]; then
          sleep_seconds="$remaining"
        fi
        sleep "$sleep_seconds"
      else
        sleep "$POLL_SECONDS"
      fi
      continue
    fi

    echo "$err_text" >&2
    exit "$aws_rc"
  fi

  now_epoch=$(date +%s)
  elapsed=$((now_epoch - start_epoch))
  if [[ "$MAX_WAIT_SECONDS" -gt 0 ]]; then
    if [[ "$elapsed" -ge "$MAX_WAIT_SECONDS" ]]; then
      emit_timeout "$elapsed"
    fi

    remaining=$((MAX_WAIT_SECONDS - elapsed))
    sleep_seconds="$POLL_SECONDS"
    if [[ "$remaining" -lt "$sleep_seconds" ]]; then
      sleep_seconds="$remaining"
    fi
    sleep "$sleep_seconds"
  else
    sleep "$POLL_SECONDS"
  fi
done
