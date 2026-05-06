#!/bin/bash
set -euo pipefail

PROFILE=""
REGION=""
OUTPUT_DIR=""
VALIDATION_SCRIPT=""
AMI_ID=""
INSTANCE_ID=""
INSTANCE_TYPE="t3.large"
SUBNET_ID=""
SECURITY_GROUP_ID=""
INSTANCE_PROFILE=""
USER_DATA_FILE=""
COMMENT="AMI validation"
KEEP_INSTANCE_ON_EXIT="false"
POLL_SECONDS=30
STALL_SECONDS=600
LAUNCHED_INSTANCE="false"
VALIDATION_EXIT_CODE=0
TAGS=()

usage() {
  cat <<'EOF'
Usage:
  bash scripts/launch-and-validate.sh \
    --profile <aws-profile> \
    --region <region> \
    --output-dir <outdir> \
    --validation-script <script.sh> \
    [--ami-id <ami-id> | --instance-id <i-xxx>] \
    [--instance-type t3.large] \
    [--subnet-id <subnet-id>] \
    [--security-group-id <sg-id>] \
    [--instance-profile <profile-name>] \
    [--user-data-file <file>] \
    [--comment <text>] \
    [--tag Key=Value]... \
    [--keep-instance-on-exit true|false] \
    [--poll-seconds 30] \
    [--stall-seconds 600]
EOF
}

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

jq_summary_status() {
  jq -r '.CommandInvocations[0].Status // "NotRun"' "${OUTPUT_DIR}/command-invocation.json" 2>/dev/null || printf 'NotRun\n'
}

capture_failure_artifacts() {
  if [[ -z "${INSTANCE_ID}" ]]; then
    return 0
  fi
  if [[ "${VALIDATION_EXIT_CODE}" -eq 0 ]]; then
    return 0
  fi

  aws ec2 describe-instances \
    --instance-ids "${INSTANCE_ID}" \
    --profile "${PROFILE}" \
    --region "${REGION}" \
    --output json > "${OUTPUT_DIR}/instance-description.json" || true

  aws ec2 describe-instance-status \
    --instance-ids "${INSTANCE_ID}" \
    --include-all-instances \
    --profile "${PROFILE}" \
    --region "${REGION}" \
    --output json > "${OUTPUT_DIR}/instance-status-final.json" || true

  aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=${INSTANCE_ID}" \
    --profile "${PROFILE}" \
    --region "${REGION}" \
    --output json > "${OUTPUT_DIR}/ssm-instance-info-final.json" || true

  aws ec2 get-console-output \
    --instance-id "${INSTANCE_ID}" \
    --latest \
    --profile "${PROFILE}" \
    --region "${REGION}" \
    --output json > "${OUTPUT_DIR}/console-output.json" || true

  jq -r '.Output // ""' "${OUTPUT_DIR}/console-output.json" \
    > "${OUTPUT_DIR}/console-output-tail.txt" 2>/dev/null || true
}

cleanup() {
  capture_failure_artifacts

  if [[ "${LAUNCHED_INSTANCE}" != "true" ]]; then
    return 0
  fi
  if [[ "${KEEP_INSTANCE_ON_EXIT}" == "true" ]]; then
    log "Keeping launched instance for debugging: ${INSTANCE_ID}"
    return 0
  fi
  if [[ -n "${INSTANCE_ID}" ]]; then
    log "Terminating launched instance: ${INSTANCE_ID}"
    aws ec2 terminate-instances \
      --instance-ids "${INSTANCE_ID}" \
      --profile "${PROFILE}" \
      --region "${REGION}" >/dev/null || true
  fi
}
trap cleanup EXIT

build_tags_json() {
  local jq_args=()
  local expr='['
  local pair key value idx=0
  local source_tags=("${TAGS[@]}")

  if [[ "${#source_tags[@]}" -eq 0 ]]; then
    source_tags=("Name=ami-validation-ssm" "purpose=ami-validation")
  fi

  for pair in "${source_tags[@]}"; do
    key="${pair%%=*}"
    value="${pair#*=}"
    jq_args+=(--arg "k${idx}" "${key}" --arg "v${idx}" "${value}")
    expr+="{Key:\$k${idx},Value:\$v${idx}},"
    idx=$((idx + 1))
  done

  expr="${expr%,}]"
  jq -cn "${jq_args[@]}" "${expr}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
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
    --validation-script)
      VALIDATION_SCRIPT="$2"
      shift 2
      ;;
    --ami-id)
      AMI_ID="$2"
      shift 2
      ;;
    --instance-id)
      INSTANCE_ID="$2"
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
    --comment)
      COMMENT="$2"
      shift 2
      ;;
    --tag)
      TAGS+=("$2")
      shift 2
      ;;
    --keep-instance-on-exit)
      KEEP_INSTANCE_ON_EXIT="$2"
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

if [[ -z "${PROFILE}" || -z "${REGION}" || -z "${OUTPUT_DIR}" || -z "${VALIDATION_SCRIPT}" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -f "${VALIDATION_SCRIPT}" ]]; then
  printf 'Missing validation script: %s\n' "${VALIDATION_SCRIPT}" >&2
  exit 2
fi

if [[ -n "${AMI_ID}" && -n "${INSTANCE_ID}" ]]; then
  printf 'Use either --ami-id or --instance-id, not both\n' >&2
  exit 2
fi

if [[ -z "${AMI_ID}" && -z "${INSTANCE_ID}" ]]; then
  printf 'One of --ami-id or --instance-id is required\n' >&2
  exit 2
fi

if [[ -n "${AMI_ID}" ]]; then
  if [[ -z "${SUBNET_ID}" || -z "${SECURITY_GROUP_ID}" || -z "${INSTANCE_PROFILE}" ]]; then
    printf 'Launch mode requires --subnet-id, --security-group-id, and --instance-profile\n' >&2
    exit 2
  fi
fi

mkdir -p "${OUTPUT_DIR}"

wait_for_instance_ok() {
  local instance_id="$1"
  local last_state=""
  local change_epoch
  change_epoch="$(date +%s)"

  while true; do
    local status_json current now_epoch
    status_json="$(
      aws ec2 describe-instance-status \
        --instance-ids "${instance_id}" \
        --include-all-instances \
        --profile "${PROFILE}" \
        --region "${REGION}" \
        --output json
    )"
    printf '%s\n' "${status_json}" > "${OUTPUT_DIR}/instance-status.json"
    current="$(printf '%s' "${status_json}" | jq -r '.InstanceStatuses[0] | "\(.InstanceState.Name // "pending")/\(.SystemStatus.Status // "unknown")/\(.InstanceStatus.Status // "unknown")"')"
    if [[ "${current}" != "${last_state}" ]]; then
      log "Instance status: ${current}"
      last_state="${current}"
      change_epoch="$(date +%s)"
    fi
    if [[ "${current}" == "running/ok/ok" ]]; then
      return 0
    fi
    now_epoch="$(date +%s)"
    if (( now_epoch - change_epoch >= STALL_SECONDS )); then
      log "Instance status stalled for ${STALL_SECONDS}s"
      return 3
    fi
    sleep "${POLL_SECONDS}"
  done
}

wait_for_ssm_online() {
  local instance_id="$1"
  local last_status=""
  local change_epoch
  change_epoch="$(date +%s)"

  while true; do
    local ssm_json ping_status now_epoch
    ssm_json="$(
      aws ssm describe-instance-information \
        --filters "Key=InstanceIds,Values=${instance_id}" \
        --profile "${PROFILE}" \
        --region "${REGION}" \
        --output json
    )"
    printf '%s\n' "${ssm_json}" > "${OUTPUT_DIR}/ssm-instance-info.json"
    ping_status="$(printf '%s' "${ssm_json}" | jq -r '.InstanceInformationList[0].PingStatus // "Missing"')"
    if [[ "${ping_status}" != "${last_status}" ]]; then
      log "SSM ping status: ${ping_status}"
      last_status="${ping_status}"
      change_epoch="$(date +%s)"
    fi
    if [[ "${ping_status}" == "Online" ]]; then
      return 0
    fi
    now_epoch="$(date +%s)"
    if (( now_epoch - change_epoch >= STALL_SECONDS )); then
      log "SSM readiness stalled for ${STALL_SECONDS}s"
      return 4
    fi
    sleep "${POLL_SECONDS}"
  done
}

run_validation() {
  local command_id
  local params_file="${OUTPUT_DIR}/send-command-params.json"
  local remote_script="/tmp/ami-validation-ssm.sh"

  python3 - "${VALIDATION_SCRIPT}" "${params_file}" "${remote_script}" <<'PY'
import json
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
params_path = Path(sys.argv[2])
remote_path = sys.argv[3]
script = script_path.read_text()
command = (
    f"cat > {remote_path} <<'EOF'\n"
    + script
    + "\nEOF\n"
    + f"sudo bash {remote_path}"
)
params_path.write_text(json.dumps({"commands": [command]}))
PY

  command_id="$(
    aws ssm send-command \
      --instance-ids "${INSTANCE_ID}" \
      --document-name AWS-RunShellScript \
      --parameters "file://${params_file}" \
      --comment "${COMMENT}" \
      --profile "${PROFILE}" \
      --region "${REGION}" \
      --output json | tee "${OUTPUT_DIR}/send-command.json" | jq -r '.Command.CommandId'
  )"
  log "SSM command id: ${command_id}"

  local last_status=""
  local change_epoch
  change_epoch="$(date +%s)"

  while true; do
    local invocation_json status now_epoch
    invocation_json="$(
      aws ssm list-command-invocations \
        --command-id "${command_id}" \
        --details \
        --profile "${PROFILE}" \
        --region "${REGION}" \
        --output json
    )"
    printf '%s\n' "${invocation_json}" > "${OUTPUT_DIR}/command-invocation.json"
    status="$(printf '%s' "${invocation_json}" | jq -r '.CommandInvocations[0].Status // "Pending"')"
    if [[ "${status}" != "${last_status}" ]]; then
      log "Validation status: ${status}"
      last_status="${status}"
      change_epoch="$(date +%s)"
    fi
    case "${status}" in
      Success)
        return 0
        ;;
      Cancelled|TimedOut|Failed|Cancelling)
        return 5
        ;;
    esac
    now_epoch="$(date +%s)"
    if (( now_epoch - change_epoch >= STALL_SECONDS )); then
      log "Validation status stalled for ${STALL_SECONDS}s"
      return 6
    fi
    sleep "${POLL_SECONDS}"
  done
}

if [[ -n "${AMI_ID}" ]]; then
  log "Launching validation instance from ${AMI_ID}"
  TAGS_JSON="$(build_tags_json)"
  TAG_SPECS_JSON="$(
    jq -cn \
      --argjson tags "${TAGS_JSON}" \
      '[{"ResourceType":"instance","Tags":$tags},{"ResourceType":"volume","Tags":$tags},{"ResourceType":"network-interface","Tags":$tags}]'
  )"
  RUN_ARGS=(
    --image-id "${AMI_ID}"
    --instance-type "${INSTANCE_TYPE}"
    --subnet-id "${SUBNET_ID}"
    --security-group-ids "${SECURITY_GROUP_ID}"
    --iam-instance-profile "Name=${INSTANCE_PROFILE}"
    --tag-specifications "${TAG_SPECS_JSON}"
    --profile "${PROFILE}"
    --region "${REGION}"
    --output json
  )
  if [[ -n "${USER_DATA_FILE}" ]]; then
    RUN_ARGS+=(--user-data "file://${USER_DATA_FILE}")
  fi
  aws ec2 run-instances "${RUN_ARGS[@]}" > "${OUTPUT_DIR}/launch.json"
  INSTANCE_ID="$(jq -r '.Instances[0].InstanceId' "${OUTPUT_DIR}/launch.json")"
  LAUNCHED_INSTANCE="true"
  log "Launched instance: ${INSTANCE_ID}"
else
  log "Reusing instance: ${INSTANCE_ID}"
fi

printf '%s\n' "${INSTANCE_ID}" > "${OUTPUT_DIR}/instance-id.txt"

wait_for_instance_ok "${INSTANCE_ID}" || VALIDATION_EXIT_CODE=$?

if [[ "${VALIDATION_EXIT_CODE}" -eq 0 ]]; then
  wait_for_ssm_online "${INSTANCE_ID}" || VALIDATION_EXIT_CODE=$?
fi

if [[ "${VALIDATION_EXIT_CODE}" -eq 0 ]]; then
  run_validation || VALIDATION_EXIT_CODE=$?
fi

jq -n \
  --arg instance_id "${INSTANCE_ID}" \
  --arg launched_instance "${LAUNCHED_INSTANCE}" \
  --arg keep_instance_on_exit "${KEEP_INSTANCE_ON_EXIT}" \
  --arg validation_script "${VALIDATION_SCRIPT}" \
  --arg validation_status "$(jq_summary_status)" \
  --argjson validation_exit_code "${VALIDATION_EXIT_CODE}" \
  '{
    instance_id: $instance_id,
    launched_instance: ($launched_instance == "true"),
    keep_instance_on_exit: ($keep_instance_on_exit == "true"),
    validation_script: $validation_script,
    validation_status: $validation_status,
    validation_exit_code: $validation_exit_code,
    console_output_path: (if $validation_exit_code == 0 then null else "console-output.json" end),
    instance_description_path: (if $validation_exit_code == 0 then null else "instance-description.json" end)
  }' > "${OUTPUT_DIR}/summary.json"

exit "${VALIDATION_EXIT_CODE}"
