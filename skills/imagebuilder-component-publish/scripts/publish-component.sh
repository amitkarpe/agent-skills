#!/bin/bash
set -euo pipefail

COMPONENT_FILE=""
VERSION=""
PROFILE=""
REGION=""
OUTPUT_DIR=""
PLATFORM="Linux"
CHECK_ONLY="false"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/publish-component.sh \
    --component-file <component.yaml> \
    --version <semantic-version> \
    --profile <aws-profile> \
    --region <region> \
    --output-dir <outdir> \
    [--platform Linux] \
    [--check-only]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --component-file)
      COMPONENT_FILE="$2"
      shift 2
      ;;
    --version)
      VERSION="$2"
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
    --platform)
      PLATFORM="$2"
      shift 2
      ;;
    --check-only)
      CHECK_ONLY="true"
      shift 1
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

if [[ -z "${COMPONENT_FILE}" || -z "${VERSION}" || -z "${PROFILE}" || -z "${REGION}" || -z "${OUTPUT_DIR}" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -f "${COMPONENT_FILE}" ]]; then
  printf 'Missing component file: %s\n' "${COMPONENT_FILE}" >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}"

python3 - "${COMPONENT_FILE}" "${OUTPUT_DIR}/component-meta.json" <<'PY'
import json
import sys
from pathlib import Path
import yaml

component_path = Path(sys.argv[1])
meta_path = Path(sys.argv[2])
data = yaml.safe_load(component_path.read_text())
name = data.get("name")
description = data.get("description", "")
if not name:
    raise SystemExit("component YAML missing top-level name")
meta_path.write_text(json.dumps({"name": name, "description": description}))
PY

NAME="$(jq -r '.name' "${OUTPUT_DIR}/component-meta.json")"
DESCRIPTION="$(jq -r '.description' "${OUTPUT_DIR}/component-meta.json")"
printf '%s\n' "${NAME}" > "${OUTPUT_DIR}/component-name.txt"
ACCOUNT_ID="$(aws sts get-caller-identity --profile "${PROFILE}" --region "${REGION}" --query Account --output text)"
COMPONENT_ARN="arn:aws:imagebuilder:${REGION}:${ACCOUNT_ID}:component/${NAME,,}/${VERSION}/1"

EXISTS="false"
if aws imagebuilder get-component \
  --component-build-version-arn "${COMPONENT_ARN}" \
  --profile "${PROFILE}" \
  --region "${REGION}" > "${OUTPUT_DIR}/get-component.json" 2>/dev/null; then
  EXISTS="true"
fi

printf '%s\n' "${COMPONENT_ARN}" > "${OUTPUT_DIR}/component-arn.txt"

jq -n \
  --arg component_file "${COMPONENT_FILE}" \
  --arg name "${NAME}" \
  --arg description "${DESCRIPTION}" \
  --arg version "${VERSION}" \
  --arg region "${REGION}" \
  --arg account_id "${ACCOUNT_ID}" \
  --arg component_arn "${COMPONENT_ARN}" \
  --arg platform "${PLATFORM}" \
  --arg check_only "${CHECK_ONLY}" \
  --arg exists "${EXISTS}" \
  '{
    component_file: $component_file,
    name: $name,
    description: $description,
    version: $version,
    region: $region,
    account_id: $account_id,
    component_arn: $component_arn,
    platform: $platform,
    check_only: ($check_only == "true"),
    exists: ($exists == "true")
  }' > "${OUTPUT_DIR}/plan.json"

if [[ "${EXISTS}" == "true" ]]; then
  jq -n --arg component_arn "${COMPONENT_ARN}" '{created: false, exists: true, component_arn: $component_arn}' > "${OUTPUT_DIR}/result.json"
  printf '%s\n' "${COMPONENT_ARN}"
  exit 0
fi

if [[ "${CHECK_ONLY}" == "true" ]]; then
  jq -n --arg component_arn "${COMPONENT_ARN}" '{created: false, exists: false, check_only: true, component_arn: $component_arn}' > "${OUTPUT_DIR}/result.json"
  printf '%s\n' "${COMPONENT_ARN}"
  exit 0
fi

aws imagebuilder create-component \
  --name "${NAME}" \
  --semantic-version "${VERSION}" \
  --description "${DESCRIPTION}" \
  --platform "${PLATFORM}" \
  --data "file://${COMPONENT_FILE}" \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --output json > "${OUTPUT_DIR}/create-component.json"

jq -n --arg component_arn "${COMPONENT_ARN}" '{created: true, exists: false, component_arn: $component_arn}' > "${OUTPUT_DIR}/result.json"
printf '%s\n' "${COMPONENT_ARN}"
