#!/usr/bin/env bash
# inspector_cis_create_or_recover_scan.sh
# Create a new Inspector CIS scan config, or recover an existing one by ARN.
#
# New scan:   omit --scan-config-arn; requires --scan-name
# Recovery:   pass --scan-config-arn; skips creation
#
# Outputs:
#   scan-config.json        raw scan configuration from Inspector
#   scan-config-arn.txt     the config ARN (for use by fetch script)
#   recovery-note.txt       written instead of scan-config.json on recovery
set -euo pipefail

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found (required for JSON parsing)"; exit 1; }

usage() {
  echo "Usage: $0 --profile <p> --region <r> --output-dir <dir>"
  echo "          [--scan-config-arn <arn>]  # recovery mode"
  echo "          [--instance-id <i-xxx>] [--scan-name <name>] [--security-level LEVEL_1|LEVEL_2]  # create mode"
  exit 1
}

PROFILE="" REGION="" INSTANCE_ID="" OUTPUT_DIR=""
SCAN_CONFIG_ARN="" SCAN_NAME="" SECURITY_LEVEL="LEVEL_2"

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)          PROFILE="$2";          shift 2 ;;
    --region)           REGION="$2";           shift 2 ;;
    --instance-id)      INSTANCE_ID="$2";      shift 2 ;;
    --output-dir)       OUTPUT_DIR="$2";       shift 2 ;;
    --scan-config-arn)  SCAN_CONFIG_ARN="$2";  shift 2 ;;
    --scan-name)        SCAN_NAME="$2";        shift 2 ;;
    --security-level)   SECURITY_LEVEL="$2";   shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$PROFILE" || -z "$REGION" || -z "$OUTPUT_DIR" ]] && usage

# Validate required params based on mode
if [[ -z "$SCAN_CONFIG_ARN" ]]; then
  # Create mode: instance-id and scan-name required
  [[ -z "$INSTANCE_ID" ]] && { echo "ERROR: --instance-id required when creating a new scan"; exit 1; }
  [[ -z "$SCAN_NAME" ]] && { echo "ERROR: --scan-name required when creating a new scan"; exit 1; }
fi

AWS="aws --profile $PROFILE --region $REGION"
mkdir -p "$OUTPUT_DIR"
log() { echo "[create-or-recover] $*"; }

# --- recovery path ---
if [[ -n "$SCAN_CONFIG_ARN" ]]; then
  log "Recovery mode — using existing config ARN: $SCAN_CONFIG_ARN"

  CONFIG_JSON=$($AWS inspector2 list-cis-scan-configurations \
    --query "scanConfigurations[?scanConfigurationArn=='$SCAN_CONFIG_ARN'] | [0]" \
    --output json)
  echo "$CONFIG_JSON" > "$OUTPUT_DIR/scan-config.json"
  echo "$SCAN_CONFIG_ARN" > "$OUTPUT_DIR/scan-config-arn.txt"

  cat > "$OUTPUT_DIR/recovery-note.txt" <<EOF
Recovery mode: scan config ARN was provided, no new config created.
Config ARN: $SCAN_CONFIG_ARN
Config saved to: $OUTPUT_DIR/scan-config.json
EOF

  log "Recovery complete. Config ARN saved to $OUTPUT_DIR/scan-config-arn.txt"
  exit 0
fi

# --- create path ---
log "Creating new CIS scan config: $SCAN_NAME (level: $SECURITY_LEVEL, target: $INSTANCE_ID)"

# Check for existing configs targeting the same instance_id tag
log "Checking for existing scan configs targeting instance_id=$INSTANCE_ID..."
EXISTING_ARNS=$($AWS inspector2 list-cis-scan-configurations --output json | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
target_id = '$INSTANCE_ID'
arns = []
for cfg in data.get('scanConfigurations', []):
    tags = cfg.get('targets', {}).get('targetResourceTags', {})
    if 'instance_id' in tags and target_id in tags['instance_id']:
        arns.append(cfg['scanConfigurationArn'])
print(' '.join(arns))
" 2>/dev/null || echo "")

if [[ -n "$EXISTING_ARNS" ]]; then
  log "Found existing scan config(s) for instance_id=$INSTANCE_ID — deleting to avoid ConflictException"
  for ARN in $EXISTING_ARNS; do
    $AWS inspector2 delete-cis-scan-configuration --scan-configuration-arn "$ARN" >/dev/null 2>&1 || true
    log "  Deleted: $ARN"
  done
  log "Waiting 15s for conflict to clear..."
  sleep 15
else
  log "No existing configs found — proceeding with creation"
fi

CONFIG_JSON=$($AWS inspector2 create-cis-scan-configuration \
  --scan-name "$SCAN_NAME" \
  --security-level "$SECURITY_LEVEL" \
  --targets "{\"accountIds\":[\"SELF\"],\"targetResourceTags\":{\"instance_id\":[\"$INSTANCE_ID\"]}}" \
  --schedule '{"oneTime":{}}' \
  --output json 2>&1)

# If name conflict, append timestamp and retry once
if echo "$CONFIG_JSON" | grep -q 'already exists\|ConflictException'; then
  SCAN_NAME="${SCAN_NAME}-$(date +%H%M%S)"
  log "Name conflict — retrying with: $SCAN_NAME"
  CONFIG_JSON=$($AWS inspector2 create-cis-scan-configuration \
    --scan-name "$SCAN_NAME" \
    --security-level "$SECURITY_LEVEL" \
    --targets "{\"accountIds\":[\"SELF\"],\"targetResourceTags\":{\"instance_id\":[\"$INSTANCE_ID\"]}}" \
    --schedule '{"oneTime":{}}' \
    --output json)
fi

SCAN_CONFIG_ARN=$(echo "$CONFIG_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['scanConfigurationArn'])")

# fetch full config and save
FULL_CONFIG=$($AWS inspector2 list-cis-scan-configurations \
  --query "scanConfigurations[?scanConfigurationArn=='$SCAN_CONFIG_ARN'] | [0]" \
  --output json)
echo "$FULL_CONFIG" > "$OUTPUT_DIR/scan-config.json"
echo "$SCAN_CONFIG_ARN" > "$OUTPUT_DIR/scan-config-arn.txt"

log "Scan config created."
log "  Config ARN: $SCAN_CONFIG_ARN"
log "  Saved to:   $OUTPUT_DIR/scan-config.json"
log "  ARN file:   $OUTPUT_DIR/scan-config-arn.txt"
