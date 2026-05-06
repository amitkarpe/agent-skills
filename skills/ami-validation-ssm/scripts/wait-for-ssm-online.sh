#!/bin/bash
set -euo pipefail

INSTANCE_ID=""
PROFILE=""
REGION=""
OUTPUT_DIR=""
PREFIX="instance"
POLL_SECONDS=30
STALL_SECONDS=600

usage() {
  cat <<'EOF'
Usage:
  bash scripts/wait-for-ssm-online.sh \
    --instance-id <i-xxx> \
    --profile <aws-profile> \
    --region <region> \
    --output-dir <outdir> \
    [--prefix instance] \
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
    --prefix)
      PREFIX="$2"
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

mkdir -p "${OUTPUT_DIR}"
INFO_FILE="${OUTPUT_DIR}/${PREFIX}-ssm-instance-info.json"

LAST_STATUS=""
CHANGE_EPOCH="$(date +%s)"

while true; do
  SSM_JSON="$(
    aws ssm describe-instance-information \
      --filters "Key=InstanceIds,Values=${INSTANCE_ID}" \
      --profile "${PROFILE}" \
      --region "${REGION}" \
      --output json
  )"
  printf '%s\n' "${SSM_JSON}" > "${INFO_FILE}"
  PING_STATUS="$(printf '%s' "${SSM_JSON}" | jq -r '.InstanceInformationList[0].PingStatus // "Missing"')"

  if [[ "${PING_STATUS}" != "${LAST_STATUS}" ]]; then
    log "SSM ping status: ${PING_STATUS}"
    LAST_STATUS="${PING_STATUS}"
    CHANGE_EPOCH="$(date +%s)"
  fi

  if [[ "${PING_STATUS}" == "Online" ]]; then
    exit 0
  fi

  NOW_EPOCH="$(date +%s)"
  if (( NOW_EPOCH - CHANGE_EPOCH >= STALL_SECONDS )); then
    log "SSM readiness stalled for ${STALL_SECONDS}s"
    exit 4
  fi

  sleep "${POLL_SECONDS}"
done
