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
  bash scripts/wait-for-instance-ok.sh \
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
STATUS_FILE="${OUTPUT_DIR}/${PREFIX}-instance-status.json"

LAST_STATE=""
CHANGE_EPOCH="$(date +%s)"

while true; do
  STATUS_JSON="$(
    aws ec2 describe-instance-status \
      --instance-ids "${INSTANCE_ID}" \
      --include-all-instances \
      --profile "${PROFILE}" \
      --region "${REGION}" \
      --output json
  )"
  printf '%s\n' "${STATUS_JSON}" > "${STATUS_FILE}"
  CURRENT="$(printf '%s' "${STATUS_JSON}" | jq -r '.InstanceStatuses[0] | "\(.InstanceState.Name // "pending")/\(.SystemStatus.Status // "unknown")/\(.InstanceStatus.Status // "unknown")"')"

  if [[ "${CURRENT}" != "${LAST_STATE}" ]]; then
    log "Instance status: ${CURRENT}"
    LAST_STATE="${CURRENT}"
    CHANGE_EPOCH="$(date +%s)"
  fi

  if [[ "${CURRENT}" == "running/ok/ok" ]]; then
    exit 0
  fi

  NOW_EPOCH="$(date +%s)"
  if (( NOW_EPOCH - CHANGE_EPOCH >= STALL_SECONDS )); then
    log "Instance status stalled for ${STALL_SECONDS}s"
    exit 3
  fi

  sleep "${POLL_SECONDS}"
done
