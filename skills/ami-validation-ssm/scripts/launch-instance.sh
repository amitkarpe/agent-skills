#!/bin/bash
set -euo pipefail

AMI_ID=""
PROFILE=""
REGION=""
OUTPUT_DIR=""
PREFIX="instance"
INSTANCE_TYPE="t3.large"
SUBNET_ID=""
SECURITY_GROUP_ID=""
INSTANCE_PROFILE=""
USER_DATA_FILE=""
TAG_SPECIFICATIONS=""
BLOCK_DEVICE_MAPPINGS=""

usage() {
  cat <<'EOF'
Usage:
  bash scripts/launch-instance.sh \
    --ami-id <ami-id> \
    --profile <aws-profile> \
    --region <region> \
    --output-dir <outdir> \
    --instance-type <type> \
    --subnet-id <subnet-id> \
    --security-group-id <sg-id> \
    --instance-profile <profile-name> \
    [--user-data-file <file>] \
    [--tag-specifications '<spec>'] \
    [--block-device-mappings '<json>'] \
    [--prefix instance]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ami-id)
      AMI_ID="$2"
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
    --instance-type)
      INSTANCE_TYPE="$2"
      shift 2
      ;;
    --subnet-id)
      SUBNET_ID="$2"
      shift 2
      ;;
    --security-group-id)
      SECURITY_GROUP_ID="$2"
      shift 2
      ;;
    --instance-profile)
      INSTANCE_PROFILE="$2"
      shift 2
      ;;
    --user-data-file)
      USER_DATA_FILE="$2"
      shift 2
      ;;
    --tag-specifications)
      TAG_SPECIFICATIONS="$2"
      shift 2
      ;;
    --block-device-mappings)
      BLOCK_DEVICE_MAPPINGS="$2"
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

if [[ -z "${AMI_ID}" || -z "${PROFILE}" || -z "${REGION}" || -z "${OUTPUT_DIR}" || -z "${SUBNET_ID}" || -z "${SECURITY_GROUP_ID}" || -z "${INSTANCE_PROFILE}" ]]; then
  usage >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}"
LAUNCH_FILE="${OUTPUT_DIR}/${PREFIX}-launch.json"
INSTANCE_ID_FILE="${OUTPUT_DIR}/${PREFIX}-instance-id.txt"

RUN_ARGS=(
  --image-id "${AMI_ID}"
  --instance-type "${INSTANCE_TYPE}"
  --subnet-id "${SUBNET_ID}"
  --security-group-ids "${SECURITY_GROUP_ID}"
  --iam-instance-profile "Name=${INSTANCE_PROFILE}"
)

if [[ -n "${USER_DATA_FILE}" ]]; then
  RUN_ARGS+=(--user-data "file://${USER_DATA_FILE}")
fi

if [[ -n "${TAG_SPECIFICATIONS}" ]]; then
  RUN_ARGS+=(--tag-specifications "${TAG_SPECIFICATIONS}")
fi

if [[ -n "${BLOCK_DEVICE_MAPPINGS}" ]]; then
  RUN_ARGS+=(--block-device-mappings "${BLOCK_DEVICE_MAPPINGS}")
fi

INSTANCE_ID="$(
  aws ec2 run-instances \
    "${RUN_ARGS[@]}" \
    --profile "${PROFILE}" \
    --region "${REGION}" \
    --output json | tee "${LAUNCH_FILE}" | jq -r '.Instances[0].InstanceId'
)"
printf '%s\n' "${INSTANCE_ID}" > "${INSTANCE_ID_FILE}"
printf '%s\n' "${INSTANCE_ID}"
