#!/bin/bash
set -euo pipefail

IMAGE_ARN=""
PROFILE=""
REGION=""
OUTPUT_DIR=""

usage() {
  cat <<'EOF'
Usage:
  bash scripts/find-retained-builder-instance.sh \
    --image-arn <image-build-version-arn> \
    --profile <aws-profile> \
    --region <region> \
    [--output-dir <outdir>]
EOF
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
  OUTPUT_DIR="${HOME}/.AGENTS-temp/agent-skills/imagebuilder-bake-validate/find-$(date -u +'%Y%m%dT%H%M%SZ')"
fi
mkdir -p "${OUTPUT_DIR}"

INSTANCES_JSON="$(
  aws ec2 describe-instances \
    --filters \
      "Name=tag:Ec2ImageBuilderArn,Values=${IMAGE_ARN}" \
      "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --profile "${PROFILE}" \
    --region "${REGION}" \
    --output json
)"
printf '%s\n' "${INSTANCES_JSON}" > "${OUTPUT_DIR}/instances.json"

LATEST_INSTANCE_JSON="$(
  printf '%s' "${INSTANCES_JSON}" | jq '
    [
      .Reservations[].Instances[]
      | {
          InstanceId,
          State: .State.Name,
          LaunchTime,
          PrivateIpAddress,
          Name: ([.Tags[]? | select(.Key == "Name") | .Value] | first // "")
        }
    ]
    | sort_by(.LaunchTime)
    | reverse
    | .[0] // {}
  '
)"
printf '%s\n' "${LATEST_INSTANCE_JSON}" > "${OUTPUT_DIR}/latest-instance.json"

INSTANCE_ID="$(printf '%s' "${LATEST_INSTANCE_JSON}" | jq -r '.InstanceId // empty')"
if [[ -n "${INSTANCE_ID}" ]]; then
  printf '%s\n' "${INSTANCE_ID}" > "${OUTPUT_DIR}/instance-id.txt"
  printf '%s\n' "${INSTANCE_ID}"
fi
