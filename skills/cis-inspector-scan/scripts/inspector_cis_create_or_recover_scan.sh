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

valid_profile() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; }
valid_region() { [[ "$1" =~ ^[a-z]{2}(-gov)?-[a-z0-9-]+-[0-9]+$ ]]; }
valid_instance_id() { [[ "$1" =~ ^i-[0-9a-f]{8,17}$ ]]; }
valid_scan_name() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$ ]]; }
valid_scan_config_arn() {
  [[ "$1" =~ ^arn:aws[a-zA-Z0-9-]*:inspector2:[a-z0-9-]+:[0-9]{12}:cis-scan-configuration/[A-Za-z0-9-]+$ ]]
}
config_by_arn() {
  python3 -c '
import json, sys
arn = sys.argv[1]
configs = json.load(sys.stdin).get("scanConfigurations", [])
match = [config for config in configs if config.get("scanConfigurationArn") == arn]
print(json.dumps(match[0]) if match else "null")
' "$1"
}
targets_json() {
  python3 -c 'import json,sys; print(json.dumps({"accountIds":["SELF"],"targetResourceTags":{"instance_id":[sys.argv[1]]}}))' "$1"
}

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

valid_profile "$PROFILE" || { echo "ERROR: invalid profile" >&2; exit 2; }
valid_region "$REGION" || { echo "ERROR: invalid region" >&2; exit 2; }
if [[ -n "$SCAN_CONFIG_ARN" ]] && ! valid_scan_config_arn "$SCAN_CONFIG_ARN"; then echo "ERROR: invalid scan configuration ARN" >&2; exit 2; fi
if [[ -n "$INSTANCE_ID" ]] && ! valid_instance_id "$INSTANCE_ID"; then echo "ERROR: invalid instance ID" >&2; exit 2; fi
if [[ -n "$SCAN_NAME" ]] && ! valid_scan_name "$SCAN_NAME"; then echo "ERROR: invalid scan name" >&2; exit 2; fi
[[ "$SECURITY_LEVEL" == "LEVEL_1" || "$SECURITY_LEVEL" == "LEVEL_2" ]] || { echo "ERROR: invalid security level" >&2; exit 2; }

# Validate required params based on mode
if [[ -z "$SCAN_CONFIG_ARN" ]]; then
  # Create mode: instance-id and scan-name required
  [[ -z "$INSTANCE_ID" ]] && { echo "ERROR: --instance-id required when creating a new scan"; exit 1; }
  [[ -z "$SCAN_NAME" ]] && { echo "ERROR: --scan-name required when creating a new scan"; exit 1; }
fi

AWS=(aws --profile "$PROFILE" --region "$REGION")
mkdir -p "$OUTPUT_DIR"
log() { echo "[create-or-recover] $*"; }

# --- recovery path ---
if [[ -n "$SCAN_CONFIG_ARN" ]]; then
  log "Recovery mode — using existing config ARN: $SCAN_CONFIG_ARN"

  CONFIG_LIST=$("${AWS[@]}" inspector2 list-cis-scan-configurations --output json)
  CONFIG_JSON=$(printf '%s' "$CONFIG_LIST" | config_by_arn "$SCAN_CONFIG_ARN")
  echo "$CONFIG_JSON" > "$OUTPUT_DIR/scan-config.json"
  echo "$SCAN_CONFIG_ARN" > "$OUTPUT_DIR/scan-config-arn.txt"

  printf 'Recovery mode: scan config ARN was provided, no new config created.\nConfig ARN: %s\nConfig saved to: %s\n' \
    "$SCAN_CONFIG_ARN" "$OUTPUT_DIR/scan-config.json" > "$OUTPUT_DIR/recovery-note.txt"

  log "Recovery complete. Config ARN saved to $OUTPUT_DIR/scan-config-arn.txt"
  exit 0
fi

# --- create path ---
log "Creating new CIS scan config: $SCAN_NAME (level: $SECURITY_LEVEL, target: $INSTANCE_ID)"

# Check for existing configs targeting the same instance_id tag
log "Checking for existing scan configs targeting instance_id=$INSTANCE_ID..."
mapfile -t EXISTING_ARNS < <("${AWS[@]}" inspector2 list-cis-scan-configurations --output json | \
  python3 -c '
import json, sys
target_id = sys.argv[1]
for config in json.load(sys.stdin).get("scanConfigurations", []):
    tags = config.get("targets", {}).get("targetResourceTags", {})
    if target_id in tags.get("instance_id", []):
        print(config["scanConfigurationArn"])
' "$INSTANCE_ID" 2>/dev/null || true)

if [[ ${#EXISTING_ARNS[@]} -gt 0 ]]; then
  log "Found existing scan config(s) for instance_id=$INSTANCE_ID — deleting to avoid ConflictException"
  for ARN in "${EXISTING_ARNS[@]}"; do
    "${AWS[@]}" inspector2 delete-cis-scan-configuration --scan-configuration-arn "$ARN" >/dev/null 2>&1 || true
    log "  Deleted: $ARN"
  done
  log "Waiting 15s for conflict to clear..."
  sleep 15
else
  log "No existing configs found — proceeding with creation"
fi

CONFIG_JSON=$("${AWS[@]}" inspector2 create-cis-scan-configuration \
  --scan-name "$SCAN_NAME" \
  --security-level "$SECURITY_LEVEL" \
  --targets "$(targets_json "$INSTANCE_ID")" \
  --schedule '{"oneTime":{}}' \
  --output json 2>&1)

# If name conflict, append timestamp and retry once
if echo "$CONFIG_JSON" | grep -q 'already exists\|ConflictException'; then
  SCAN_NAME="${SCAN_NAME}-$(date +%H%M%S)"
  log "Name conflict — retrying with: $SCAN_NAME"
  CONFIG_JSON=$("${AWS[@]}" inspector2 create-cis-scan-configuration \
    --scan-name "$SCAN_NAME" \
    --security-level "$SECURITY_LEVEL" \
    --targets "$(targets_json "$INSTANCE_ID")" \
    --schedule '{"oneTime":{}}' \
    --output json)
fi

SCAN_CONFIG_ARN=$(printf '%s' "$CONFIG_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["scanConfigurationArn"])')

# fetch full config and save
FULL_CONFIG_LIST=$("${AWS[@]}" inspector2 list-cis-scan-configurations --output json)
FULL_CONFIG=$(printf '%s' "$FULL_CONFIG_LIST" | config_by_arn "$SCAN_CONFIG_ARN")
echo "$FULL_CONFIG" > "$OUTPUT_DIR/scan-config.json"
echo "$SCAN_CONFIG_ARN" > "$OUTPUT_DIR/scan-config-arn.txt"

log "Scan config created."
log "  Config ARN: $SCAN_CONFIG_ARN"
log "  Saved to:   $OUTPUT_DIR/scan-config.json"
log "  ARN file:   $OUTPUT_DIR/scan-config-arn.txt"
