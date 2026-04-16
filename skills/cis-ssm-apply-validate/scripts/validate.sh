#!/usr/bin/env bash
set -euo pipefail

# validate.sh - Runtime validation for SSM document apply workflow

log() { echo "[$(date -Iseconds)] $*"; }
error() { echo "[$(date -Iseconds)] ERROR: $*" >&2; exit 1; }

# Check dependencies
command -v jq >/dev/null 2>&1 || error "jq is required but not installed"
command -v aws >/dev/null 2>&1 || error "aws CLI is required but not installed"

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Required:
  --document-file PATH      Local SSM document YAML file
  --parameters-file PATH    JSON file with document parameters
  --output-dir PATH         Evidence output directory

Optional:
  --instance-id ID          Target instance (validates if provided)
  --profile NAME            AWS profile
  --region NAME             AWS region
  --allow-nonempty          Allow non-empty output directory (internal use)
EOF
  exit 1
}

DOCUMENT_FILE=""
PARAMETERS_FILE=""
OUTPUT_DIR=""
INSTANCE_ID=""
PROFILE=""
REGION=""
ALLOW_NONEMPTY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --document-file) DOCUMENT_FILE="$2"; shift 2 ;;
    --parameters-file) PARAMETERS_FILE="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --allow-nonempty) ALLOW_NONEMPTY=true; shift ;;
    *) usage ;;
  esac
done

[[ -z "$DOCUMENT_FILE" || -z "$PARAMETERS_FILE" || -z "$OUTPUT_DIR" ]] && usage

# Check output directory is empty or create it
if [[ -d "$OUTPUT_DIR" ]]; then
  if [[ "$ALLOW_NONEMPTY" == "false" ]] && [[ -n "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]]; then
    error "Output directory is not empty: $OUTPUT_DIR (use unique directory per run)"
  fi
else
  mkdir -p "$OUTPUT_DIR" || error "Failed to create output directory: $OUTPUT_DIR"
fi

LOG_FILE="$OUTPUT_DIR/validate.log"

# Redirect stdout to log file, stderr to separate error log
exec > >(tee -a "$LOG_FILE") 2> >(tee -a "$OUTPUT_DIR/validate-errors.log" >&2)

log "Starting validation"

# Validate document file exists and is readable
[[ ! -f "$DOCUMENT_FILE" ]] && error "Document file not found: $DOCUMENT_FILE"
[[ ! -r "$DOCUMENT_FILE" ]] && error "Document file not readable: $DOCUMENT_FILE"
log "Document file validated: $DOCUMENT_FILE"

# Validate parameters file exists and is valid JSON
[[ ! -f "$PARAMETERS_FILE" ]] && error "Parameters file not found: $PARAMETERS_FILE"
jq empty "$PARAMETERS_FILE" 2>/dev/null || error "Invalid JSON in parameters file: $PARAMETERS_FILE"

# Validate SSM parameter structure (must be object with string or array values)
PARAM_TYPE=$(jq -r 'type' "$PARAMETERS_FILE")
[[ "$PARAM_TYPE" != "object" ]] && error "Parameters must be a JSON object, got: $PARAM_TYPE"

# Check all values are strings or arrays of strings
INVALID_PARAMS=$(jq -r 'to_entries[] | select(.value | type != "string" and type != "array") | .key' "$PARAMETERS_FILE")
[[ -n "$INVALID_PARAMS" ]] && error "Invalid parameter values (must be string or array): $INVALID_PARAMS"

log "Parameters file validated: $PARAMETERS_FILE"

# Build AWS CLI args
AWS_ARGS=()
[[ -n "$PROFILE" ]] && AWS_ARGS+=(--profile "$PROFILE")
[[ -n "$REGION" ]] && AWS_ARGS+=(--region "$REGION")

# Validate instance if provided
if [[ -n "$INSTANCE_ID" ]]; then
  log "Validating instance: $INSTANCE_ID"
  aws ec2 describe-instances ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].{State:State.Name,Platform:PlatformDetails}' \
    > "$OUTPUT_DIR/instance-info.json" || error "Failed to describe instance: $INSTANCE_ID"
  
  STATE=$(jq -r '.State' "$OUTPUT_DIR/instance-info.json")
  [[ "$STATE" != "running" ]] && error "Instance not running: $STATE"
  log "Instance state: $STATE"
  
  aws ssm describe-instance-information ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    > "$OUTPUT_DIR/ssm-agent-info.json" || error "Failed to get SSM agent info"
  
  PING_STATUS=$(jq -r '.InstanceInformationList[0].PingStatus // "Unknown"' "$OUTPUT_DIR/ssm-agent-info.json")
  [[ "$PING_STATUS" != "Online" ]] && error "SSM agent not online: $PING_STATUS"
  log "SSM agent status: $PING_STATUS"
fi

log "Validation passed"
echo "Document: $DOCUMENT_FILE"
echo "Parameters: $PARAMETERS_FILE"
echo "Evidence: $OUTPUT_DIR"
