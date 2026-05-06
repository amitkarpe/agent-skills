#!/bin/bash
set -euo pipefail

INSTANCE_ID=""
PROFILE=""
REGION=""
OUTPUT_DIR=""
COMMENT="AMI validation"
PREFIX="command"
COMMANDS_JSON=""
COMMANDS_FILE=""
POLL_SECONDS=30
STALL_SECONDS=600

usage() {
  cat <<'EOF'
Usage:
  bash scripts/send-command-and-wait.sh \
    --instance-id <i-xxx> \
    --profile <aws-profile> \
    --region <region> \
    --output-dir <outdir> \
    --comment <text> \
    [--prefix command] \
    [--commands-json '<json-array>'] \
    [--commands-file <json-file>] \
    [--poll-seconds 30] \
    [--stall-seconds 600]
EOF
}

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instance-id)
      INSTANCE_ID="$2"
      shift 2
      ;;
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --comment)
      COMMENT="$2"
      shift 2
      ;;
    --prefix)
      PREFIX="$2"
      shift 2
      ;;
    --commands-json)
      COMMANDS_JSON="$2"
      shift 2
      ;;
    --commands-file)
      COMMANDS_FILE="$2"
      shift 2
      ;;
    --poll-seconds)
      POLL_SECONDS="$2"
      shift 2
      ;;
    --stall-seconds)
      STALL_SECONDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${INSTANCE_ID}" || -z "${PROFILE}" || -z "${REGION}" || -z "${OUTPUT_DIR}" ]]; then
  usage >&2
  exit 2
fi

if [[ -n "${COMMANDS_JSON}" && -n "${COMMANDS_FILE}" ]]; then
  printf 'Use either --commands-json or --commands-file, not both\n' >&2
  exit 2
fi

if [[ -z "${COMMANDS_JSON}" && -z "${COMMANDS_FILE}" ]]; then
  printf 'One of --commands-json or --commands-file is required\n' >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}"
SEND_FILE="${OUTPUT_DIR}/${PREFIX}-send-command.json"
INVOCATION_FILE="${OUTPUT_DIR}/${PREFIX}-command-invocation.json"
COMMAND_ID_FILE="${OUTPUT_DIR}/${PREFIX}-command-id.txt"

PARAMS_ARG=()
if [[ -n "${COMMANDS_FILE}" ]]; then
  PARAMS_ARG=(--parameters "file://${COMMANDS_FILE}")
else
  PARAMS_ARG=(--parameters "commands=${COMMANDS_JSON}")
fi

COMMAND_ID="$(
  aws ssm send-command \
    --instance-ids "${INSTANCE_ID}" \
    --document-name AWS-RunShellScript \
    "${PARAMS_ARG[@]}" \
    --comment "${COMMENT}" \
    --profile "${PROFILE}" \
    --region "${REGION}" \
    --output json | tee "${SEND_FILE}" | jq -r '.Command.CommandId'
)"
printf '%s\n' "${COMMAND_ID}" > "${COMMAND_ID_FILE}"
log "SSM command id (${COMMENT}): ${COMMAND_ID}"

LAST_STATUS=""
CHANGE_EPOCH="$(date +%s)"

while true; do
  INVOCATION_JSON="$(
    aws ssm list-command-invocations \
      --command-id "${COMMAND_ID}" \
      --details \
      --profile "${PROFILE}" \
      --region "${REGION}" \
      --output json
  )"
  printf '%s\n' "${INVOCATION_JSON}" > "${INVOCATION_FILE}"
  STATUS="$(printf '%s' "${INVOCATION_JSON}" | jq -r '.CommandInvocations[0].Status // "Pending"')"

  if [[ "${STATUS}" != "${LAST_STATUS}" ]]; then
    log "Validation command status (${COMMENT}): ${STATUS}"
    LAST_STATUS="${STATUS}"
    CHANGE_EPOCH="$(date +%s)"
  fi

  case "${STATUS}" in
    Success)
      printf '%s\n' "${COMMAND_ID}"
      exit 0
      ;;
    Cancelled|TimedOut|Failed|Cancelling)
      exit 5
      ;;
  esac

  NOW_EPOCH="$(date +%s)"
  if (( NOW_EPOCH - CHANGE_EPOCH >= STALL_SECONDS )); then
    log "Validation command stalled for ${STALL_SECONDS}s (${COMMENT})"
    exit 6
  fi

  sleep "${POLL_SECONDS}"
done
