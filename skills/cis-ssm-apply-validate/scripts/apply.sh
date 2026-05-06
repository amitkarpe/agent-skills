#!/usr/bin/env bash
set -euo pipefail

# apply.sh - Publish/update SSM document and execute on target instance

log() { echo "[$(date -Iseconds)] $*"; }
error() { echo "[$(date -Iseconds)] ERROR: $*" >&2; exit 1; }

document_format_from_path() {
  local path="$1"
  case "${path##*.}" in
    yaml|yml) echo "YAML" ;;
    json) echo "JSON" ;;
    *) error "Unsupported document file extension for $path (expected .yaml, .yml, or .json)" ;;
  esac
}

# Check dependencies
command -v jq >/dev/null 2>&1 || error "jq is required but not installed"
command -v aws >/dev/null 2>&1 || error "aws CLI is required but not installed"

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Required:
  --document-name NAME      SSM document name
  --document-file PATH      Local SSM document YAML or JSON file
  --parameters-file PATH    JSON file with document parameters
  --instance-id ID          Target instance
  --output-dir PATH         Evidence output directory

Optional:
  --profile NAME            AWS profile
  --region NAME             AWS region
  --dry-run                 Validate only, skip apply
  --wait-timeout SECONDS    Command wait timeout (default: 600)
EOF
  exit 1
}

DOCUMENT_NAME=""
DOCUMENT_FILE=""
PARAMETERS_FILE=""
INSTANCE_ID=""
OUTPUT_DIR=""
PROFILE=""
REGION=""
DRY_RUN=false
WAIT_TIMEOUT=600
SKIP_UPLOAD=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --document-name) DOCUMENT_NAME="$2"; shift 2 ;;
    --document-file) DOCUMENT_FILE="$2"; shift 2 ;;
    --parameters-file) PARAMETERS_FILE="$2"; shift 2 ;;
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --wait-timeout) WAIT_TIMEOUT="$2"; shift 2 ;;
    --skip-upload) SKIP_UPLOAD=true; shift ;;
    *) usage ;;
  esac
done

[[ -z "$DOCUMENT_NAME" || -z "$DOCUMENT_FILE" || -z "$PARAMETERS_FILE" || -z "$INSTANCE_ID" || -z "$OUTPUT_DIR" ]] && usage

# Check output directory is empty or create it
if [[ -d "$OUTPUT_DIR" ]]; then
  if [[ -n "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]]; then
    error "Output directory is not empty: $OUTPUT_DIR (use unique directory per run)"
  fi
else
  mkdir -p "$OUTPUT_DIR" || error "Failed to create output directory: $OUTPUT_DIR"
fi

LOG_FILE="$OUTPUT_DIR/apply.log"

# Redirect stdout to log file, stderr to separate error log
exec > >(tee -a "$LOG_FILE") 2> >(tee -a "$OUTPUT_DIR/apply-errors.log" >&2)

log "Starting apply workflow"

AWS_ARGS=()
[[ -n "$PROFILE" ]] && AWS_ARGS+=(--profile "$PROFILE")
[[ -n "$REGION" ]] && AWS_ARGS+=(--region "$REGION")
DOCUMENT_FORMAT="$(document_format_from_path "$DOCUMENT_FILE")"
NORMALIZED_PARAMETERS_FILE="$OUTPUT_DIR/parameters-normalized.json"

# Run validation first
log "Running validation"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if $DRY_RUN; then
  # Dry-run: skip instance validation
  "$SCRIPT_DIR/validate.sh" \
    --document-file "$DOCUMENT_FILE" \
    --parameters-file "$PARAMETERS_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --allow-nonempty \
    ${PROFILE:+--profile "$PROFILE"} \
    ${REGION:+--region "$REGION"} || error "Validation failed"
  
  log "DRY-RUN: Validation passed, skipping apply"
  exit 0
else
  "$SCRIPT_DIR/validate.sh" \
    --document-file "$DOCUMENT_FILE" \
    --parameters-file "$PARAMETERS_FILE" \
    --instance-id "$INSTANCE_ID" \
    --output-dir "$OUTPUT_DIR" \
    --allow-nonempty \
    ${PROFILE:+--profile "$PROFILE"} \
    ${REGION:+--region "$REGION"} || error "Validation failed"
fi

# Capture pre-mutation state for rollback
log "Capturing pre-mutation state"
if aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} --name "$DOCUMENT_NAME" &>/dev/null 2>&1; then
  aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --name "$DOCUMENT_NAME" \
    > "$OUTPUT_DIR/pre-mutation-document.json" || log "Warning: Could not capture pre-mutation state"
  
  PREV_DEFAULT=$(jq -r '.Document.DefaultVersion // "unknown"' "$OUTPUT_DIR/pre-mutation-document.json")
  echo "$PREV_DEFAULT" > "$OUTPUT_DIR/previous-default-version.txt"
  log "Previous default version: $PREV_DEFAULT"
fi

# Publish or update document
log "Publishing document: $DOCUMENT_NAME"
# Capture current default version for rollback
PREV_DOC_VERSION=$(aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
  --name "$DOCUMENT_NAME" --query 'Document.DefaultVersion' --output text 2>/dev/null || echo "")
if $SKIP_UPLOAD; then
  log "--skip-upload set: using existing default version"
  DOC_VERSION=$(aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --name "$DOCUMENT_NAME" \
    --query 'Document.DefaultVersion' --output text 2>/dev/null) || error "Document not found: $DOCUMENT_NAME"
  echo "$DOC_VERSION" > "$OUTPUT_DIR/document-version.txt"
  log "Using existing version: $DOC_VERSION"
elif aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} --name "$DOCUMENT_NAME" &>/dev/null; then
  # Content-hash check: skip upload if content is identical to current default
  CURRENT_CONTENT=$(aws ssm get-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --name "$DOCUMENT_NAME" --query 'Content' --output text 2>/dev/null || echo "")
  LOCAL_CONTENT=$(cat "$DOCUMENT_FILE")
  CURRENT_HASH=$(echo "$CURRENT_CONTENT" | md5sum | cut -d' ' -f1)
  LOCAL_HASH=$(echo "$LOCAL_CONTENT" | md5sum | cut -d' ' -f1)

  if [[ "$CURRENT_HASH" == "$LOCAL_HASH" ]]; then
    log "Content unchanged (hash: $LOCAL_HASH) — skipping upload"
    DOC_VERSION=$(aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
      --name "$DOCUMENT_NAME" --query 'Document.DefaultVersion' --output text)
    echo "$DOC_VERSION" > "$OUTPUT_DIR/document-version.txt"
    log "Using existing version: $DOC_VERSION"
  else
    log "Content changed — updating document"
    UPDATE_OUTPUT=$(aws ssm update-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
      --name "$DOCUMENT_NAME" \
      --content "file://$DOCUMENT_FILE" \
      --document-format "$DOCUMENT_FORMAT" \
      --document-version '$LATEST' \
      --output json 2>&1) || true

    if echo "$UPDATE_OUTPUT" | grep -q 'DuplicateDocumentContent'; then
      log "DuplicateDocumentContent — content identical to current version, treating as no-op"
      DOC_VERSION=$(aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
        --name "$DOCUMENT_NAME" --query 'Document.DefaultVersion' --output text)
      echo "$DOC_VERSION" > "$OUTPUT_DIR/document-version.txt"
      log "Using existing version: $DOC_VERSION"
    else
      echo "$UPDATE_OUTPUT" > "$OUTPUT_DIR/update-response.json"
      echo "$UPDATE_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0)" 2>/dev/null || \
        error "Failed to update document: $UPDATE_OUTPUT"

      DOC_VERSION=$(echo "$UPDATE_OUTPUT" | python3 -c \
        "import sys,json; print(json.load(sys.stdin)['DocumentDescription']['DocumentVersion'])")
      echo "$DOC_VERSION" > "$OUTPUT_DIR/document-version.txt"
      log "Updated to version: $DOC_VERSION"

      aws ssm update-document-default-version ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
        --name "$DOCUMENT_NAME" \
        --document-version "$DOC_VERSION" \
        > "$OUTPUT_DIR/default-version-response.json" || error "Failed to update default version"
      log "Pinned default version: $DOC_VERSION"
    fi
  fi
else
  log "Document does not exist, creating"
  aws ssm create-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --name "$DOCUMENT_NAME" \
    --content "file://$DOCUMENT_FILE" \
    --document-type "Command" \
    --document-format "$DOCUMENT_FORMAT" \
    > "$OUTPUT_DIR/create-response.json" || error "Failed to create document"

  DOC_VERSION=$(jq -r '.DocumentDescription.DocumentVersion' "$OUTPUT_DIR/create-response.json")
  echo "$DOC_VERSION" > "$OUTPUT_DIR/document-version.txt"
  log "Created version: $DOC_VERSION"
fi

# Get document metadata
aws ssm describe-document ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
  --name "$DOCUMENT_NAME" \
  > "$OUTPUT_DIR/document-metadata.json" || error "Failed to get document metadata"

# Normalize parameters so send-command always receives arrays of strings
jq '
  with_entries(
    .value |= if type == "string" then [.] else . end
  )
' "$PARAMETERS_FILE" > "$NORMALIZED_PARAMETERS_FILE" || error "Failed to normalize parameters file"
cp "$PARAMETERS_FILE" "$OUTPUT_DIR/parameters-input.json" || error "Failed to copy original parameters file"
cp "$NORMALIZED_PARAMETERS_FILE" "$OUTPUT_DIR/parameters-used.json" || error "Failed to copy normalized parameters file"

# Send command
log "Sending command to instance: $INSTANCE_ID"
aws ssm send-command ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
  --document-name "$DOCUMENT_NAME" \
  --instance-ids "$INSTANCE_ID" \
  --parameters "file://$NORMALIZED_PARAMETERS_FILE" \
  > "$OUTPUT_DIR/send-command-response.json" || error "Failed to send command"

COMMAND_ID=$(jq -r '.Command.CommandId' "$OUTPUT_DIR/send-command-response.json")
echo "$COMMAND_ID" > "$OUTPUT_DIR/command-id.txt"
log "Command ID: $COMMAND_ID"

# Wait for completion with proper polling
log "Waiting for command completion (timeout: ${WAIT_TIMEOUT}s)"
START_TIME=$(date +%s)
STATUS="Pending"
POLL_INTERVAL=20

while [[ "$STATUS" =~ ^(Pending|InProgress)$ ]]; do
  ELAPSED=$(($(date +%s) - START_TIME))
  if [[ $ELAPSED -ge $WAIT_TIMEOUT ]]; then
    log "Timeout reached after ${ELAPSED}s"
    break
  fi
  
  sleep $POLL_INTERVAL
  
  aws ssm get-command-invocation ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    > "$OUTPUT_DIR/invocation.json" 2>/dev/null || continue
  
  STATUS=$(jq -r '.Status' "$OUTPUT_DIR/invocation.json")
  log "Command status: $STATUS (${ELAPSED}s elapsed)"
done

# Final invocation details
aws ssm get-command-invocation ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  > "$OUTPUT_DIR/invocation.json" || error "Failed to get command invocation"

# Extract stdout/stderr
jq -r '.StandardOutputContent // ""' "$OUTPUT_DIR/invocation.json" > "$OUTPUT_DIR/stdout.txt"
jq -r '.StandardErrorContent // ""' "$OUTPUT_DIR/invocation.json" > "$OUTPUT_DIR/stderr.txt"

STATUS=$(jq -r '.Status' "$OUTPUT_DIR/invocation.json")
RESPONSE_CODE=$(jq -r '.ResponseCode // "unknown"' "$OUTPUT_DIR/invocation.json")
log "Command status: $STATUS, ResponseCode: $RESPONSE_CODE"

# Post-apply stdout parsing for known failure patterns
KNOWN_FAILURES=(
  "sshd -t"
  "augenrules"
  "visudo"
  "iptables-restore"
  "ip6tables-restore"
  "FAILED"
  "Error:"
  "error:"
)
STDOUT_WARNINGS=()
for pattern in "${KNOWN_FAILURES[@]}"; do
  if grep -q "$pattern" "$OUTPUT_DIR/stdout.txt" 2>/dev/null; then
    STDOUT_WARNINGS+=("$pattern")
  fi
done
if [[ ${#STDOUT_WARNINGS[@]} -gt 0 ]]; then
  log "WARNING: Known failure patterns found in stdout: ${STDOUT_WARNINGS[*]}"
  log "Review $OUTPUT_DIR/stdout.txt for details"
  echo "WARNINGS: ${STDOUT_WARNINGS[*]}" >> "$OUTPUT_DIR/summary.txt"
fi

# Post-apply validation + rollback on failure
rollback() {
  local prev_ver="$1"
  log "ROLLBACK: reverting default version to $prev_ver"
  aws ssm update-document-default-version ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
    --name "$DOCUMENT_NAME" --document-version "$prev_ver" \
    > "$OUTPUT_DIR/rollback-response.json" 2>/dev/null && \
    log "ROLLBACK: default version reverted to $prev_ver" || \
    log "ROLLBACK: failed to revert — manual intervention required"
}

if [[ "$STATUS" != "Success" ]]; then
  log "Command failed with status: $STATUS"
  if [[ -n "${PREV_DOC_VERSION:-}" && "$PREV_DOC_VERSION" != "$DOC_VERSION" ]]; then
    rollback "$PREV_DOC_VERSION"
  fi
  error "Apply failed — see $OUTPUT_DIR/stdout.txt and $OUTPUT_DIR/stderr.txt"
fi

if [[ "$RESPONSE_CODE" != "0" && "$RESPONSE_CODE" != "unknown" ]]; then
  log "Command returned non-zero response code: $RESPONSE_CODE"
  if [[ -n "${PREV_DOC_VERSION:-}" && "$PREV_DOC_VERSION" != "$DOC_VERSION" ]]; then
    rollback "$PREV_DOC_VERSION"
  fi
  error "Apply failed with response code $RESPONSE_CODE"
fi

# Check for reboot in stdout/stderr
if grep -qi "reboot" "$OUTPUT_DIR/stdout.txt" "$OUTPUT_DIR/stderr.txt" 2>/dev/null; then
  log "Reboot detected in command output, waiting for instance recovery"
  
  # Wait for instance to stop responding
  sleep 10
  
  # Wait for SSM agent to come back online (max 5 minutes)
  REBOOT_TIMEOUT=300
  REBOOT_START=$(date +%s)
  AGENT_ONLINE=false
  
  while [[ $(($(date +%s) - REBOOT_START)) -lt $REBOOT_TIMEOUT ]]; do
    if aws ssm describe-instance-information ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
      --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
      > "$OUTPUT_DIR/reboot-wait-ssm-agent.json" 2>/dev/null; then
      
      REBOOT_PING=$(jq -r '.InstanceInformationList[0].PingStatus // "Unknown"' "$OUTPUT_DIR/reboot-wait-ssm-agent.json")
      if [[ "$REBOOT_PING" == "Online" ]]; then
        log "SSM agent back online after reboot"
        AGENT_ONLINE=true
        break
      fi
    fi
    sleep 10
  done
  
  [[ "$AGENT_ONLINE" == "false" ]] && error "SSM agent did not come back online after reboot"
fi

# Verify instance is still reachable
aws ssm describe-instance-information ${AWS_ARGS[@]+"${AWS_ARGS[@]}"} \
  --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
  > "$OUTPUT_DIR/post-apply-ssm-agent.json" || log "Warning: Could not verify SSM agent post-apply"

POST_PING=$(jq -r '.InstanceInformationList[0].PingStatus // "Unknown"' "$OUTPUT_DIR/post-apply-ssm-agent.json")
log "Post-apply SSM agent status: $POST_PING"

# Terminal summary
cat > "$OUTPUT_DIR/summary.txt" <<EOF
Command ID: $COMMAND_ID
Status: $STATUS
ResponseCode: $RESPONSE_CODE
Post-apply SSM agent: $POST_PING
Document: $DOCUMENT_NAME
Version: $DOC_VERSION
EOF

log "Apply completed successfully"
