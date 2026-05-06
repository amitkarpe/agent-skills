#!/bin/bash
set -euo pipefail

IMAGE_ARN=""
PROFILE=""
REGION=""
OUTPUT_DIR=""
POLL_SECONDS=30
TIMEOUT_SECONDS=7200

usage() {
  cat <<'EOF'
Usage:
  bash scripts/poll-image.sh \
    --image-arn <image-build-version-arn> \
    --profile <aws-profile> \
    --region <region> \
    [--output-dir <outdir>] \
    [--poll-seconds 30] \
    [--timeout-seconds 7200]
EOF
}

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${OUTPUT_DIR}/status.log"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image-arn)
      IMAGE_ARN="$2"
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
    --poll-seconds)
      POLL_SECONDS="$2"
      shift 2
      ;;
    --timeout-seconds)
      TIMEOUT_SECONDS="$2"
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

if [[ -z "${IMAGE_ARN}" || -z "${PROFILE}" || -z "${REGION}" ]]; then
  usage >&2
  exit 2
fi

if [[ -z "${OUTPUT_DIR}" ]]; then
  OUTPUT_DIR="${HOME}/.AGENTS-temp/agent-skills/imagebuilder-bake-validate/poll-$(date -u +'%Y%m%dT%H%M%SZ')"
fi
mkdir -p "${OUTPUT_DIR}"
printf '%s\n' "${IMAGE_ARN}" > "${OUTPUT_DIR}/image-arn.txt"

LAST_STATUS=""
LAST_REASON=""
START_EPOCH="$(date +%s)"

while true; do
  IMAGE_JSON="$(
    aws imagebuilder get-image \
      --image-build-version-arn "${IMAGE_ARN}" \
      --profile "${PROFILE}" \
      --region "${REGION}" \
      --output json
  )"
  printf '%s\n' "${IMAGE_JSON}" > "${OUTPUT_DIR}/image.json"

  STATUS="$(printf '%s' "${IMAGE_JSON}" | jq -r '.image.state.status')"
  REASON="$(printf '%s' "${IMAGE_JSON}" | jq -r '.image.state.reason // ""')"
  AMI_ID="$(printf '%s' "${IMAGE_JSON}" | jq -r '.image.outputResources.amis[0].image // empty')"

  printf '%s\n' "${STATUS}" > "${OUTPUT_DIR}/status.txt"
  if [[ -n "${AMI_ID}" ]]; then
    printf '%s\n' "${AMI_ID}" > "${OUTPUT_DIR}/ami-id.txt"
  fi
  jq -n \
    --arg image_arn "${IMAGE_ARN}" \
    --arg status "${STATUS}" \
    --arg reason "${REASON}" \
    --arg ami_id "${AMI_ID}" \
    --arg updated_at "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    '{
      image_arn: $image_arn,
      status: $status,
      reason: (if $reason == "" then null else $reason end),
      ami_id: (if $ami_id == "" then null else $ami_id end),
      updated_at: $updated_at
    }' > "${OUTPUT_DIR}/summary.json"

  if [[ "${STATUS}" != "${LAST_STATUS}" || "${REASON}" != "${LAST_REASON}" ]]; then
    log "status=${STATUS}${REASON:+ reason=${REASON}}${AMI_ID:+ ami=${AMI_ID}}"
    LAST_STATUS="${STATUS}"
    LAST_REASON="${REASON}"
  fi

  case "${STATUS}" in
    AVAILABLE)
      exit 0
      ;;
    FAILED|CANCELLED)
      exit 1
      ;;
  esac

  NOW_EPOCH="$(date +%s)"
  if (( NOW_EPOCH - START_EPOCH >= TIMEOUT_SECONDS )); then
    log "timeout after ${TIMEOUT_SECONDS}s"
    exit 124
  fi

  sleep "${POLL_SECONDS}"
done
