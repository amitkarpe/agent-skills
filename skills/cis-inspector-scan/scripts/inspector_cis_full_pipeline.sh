#!/usr/bin/env bash
# inspector_cis_full_pipeline.sh
# Single-command wrapper: preflight → create (with conflict cleanup) → fetch (with auto-recover) → reduce
#
# Exits 0 only on valid completed scan with totalChecks > 0.
# All evidence saved to --output-dir.
set -euo pipefail

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required"; exit 1; }

valid_profile() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; }
valid_region() { [[ "$1" =~ ^[a-z]{2}(-gov)?-[a-z0-9-]+-[0-9]+$ ]]; }
valid_instance_id() { [[ "$1" =~ ^i-[0-9a-f]{8,17}$ ]]; }
valid_scan_name() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$ ]]; }

usage() {
  echo "Usage: $0 --profile <p> --region <r> --instance-id <i-xxx> --scan-name <name> --output-dir <dir>"
  echo "          [--security-level LEVEL_1|LEVEL_2] [--max-wait SECONDS]"
  exit 1
}

PROFILE="" REGION="" INSTANCE_ID="" SCAN_NAME="" OUTPUT_DIR=""
SECURITY_LEVEL="LEVEL_2"
MAX_WAIT=600  # 10 min total ceiling (2 attempts × 5 min)

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)         PROFILE="$2";         shift 2 ;;
    --region)          REGION="$2";          shift 2 ;;
    --instance-id)     INSTANCE_ID="$2";     shift 2 ;;
    --scan-name)       SCAN_NAME="$2";       shift 2 ;;
    --output-dir)      OUTPUT_DIR="$2";      shift 2 ;;
    --security-level)  SECURITY_LEVEL="$2";  shift 2 ;;
    --max-wait)        MAX_WAIT="$2";        shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$PROFILE" || -z "$REGION" || -z "$INSTANCE_ID" || -z "$SCAN_NAME" || -z "$OUTPUT_DIR" ]] && usage

valid_profile "$PROFILE" || { echo "ERROR: invalid profile" >&2; exit 2; }
valid_region "$REGION" || { echo "ERROR: invalid region" >&2; exit 2; }
valid_instance_id "$INSTANCE_ID" || { echo "ERROR: invalid instance ID" >&2; exit 2; }
valid_scan_name "$SCAN_NAME" || { echo "ERROR: invalid scan name" >&2; exit 2; }
[[ "$SECURITY_LEVEL" == "LEVEL_1" || "$SECURITY_LEVEL" == "LEVEL_2" ]] || { echo "ERROR: invalid security level" >&2; exit 2; }
[[ "$MAX_WAIT" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: invalid max wait" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUTPUT_DIR"
log() { echo "[pipeline] $*"; }

# 1. Preflight
log "Step 1/4: Preflight"
bash "$SCRIPT_DIR/inspector_cis_preflight.sh" \
  --profile "$PROFILE" --region "$REGION" \
  --instance-id "$INSTANCE_ID" --output-dir "$OUTPUT_DIR"

# 2. Create scan (auto-cleans conflicts)
log "Step 2/4: Create scan"
bash "$SCRIPT_DIR/inspector_cis_create_or_recover_scan.sh" \
  --profile "$PROFILE" --region "$REGION" \
  --instance-id "$INSTANCE_ID" \
  --scan-name "$SCAN_NAME" \
  --security-level "$SECURITY_LEVEL" \
  --output-dir "$OUTPUT_DIR"

CONFIG_ARN=$(<"$OUTPUT_DIR/scan-config-arn.txt")

# 3. Fetch with auto-recover on timeout
log "Step 3/4: Fetch results (max-wait=${MAX_WAIT}s)"
FETCH_OK=false
for attempt in 1 2; do
  if bash "$SCRIPT_DIR/inspector_cis_fetch_results.sh" \
      --profile "$PROFILE" --region "$REGION" \
      --scan-config-arn "$CONFIG_ARN" \
      --output-dir "$OUTPUT_DIR"; then
    FETCH_OK=true
    break
  fi
  if [[ $attempt -lt 2 ]]; then
    log "Fetch timed out (attempt $attempt) — waiting 60s then recovering..."
    sleep 60
    bash "$SCRIPT_DIR/inspector_cis_create_or_recover_scan.sh" \
      --profile "$PROFILE" --region "$REGION" \
      --scan-config-arn "$CONFIG_ARN" \
      --output-dir "$OUTPUT_DIR"
  fi
done

if [[ "$FETCH_OK" != true ]]; then
  log "ERROR: Scan did not complete within max-wait. Config ARN: $CONFIG_ARN"
  log "Re-run with: $0 --scan-config-arn $CONFIG_ARN ..."
  exit 1
fi

# 4. Reduce to failed controls
log "Step 4/4: Reduce failed controls"
bash "$SCRIPT_DIR/inspector_cis_reduce_failed_controls.sh" --output-dir "$OUTPUT_DIR"

# Summary
python3 -c '
import json, sys
with open(sys.argv[1]) as handle:
    scan = json.load(handle)
with open(sys.argv[2]) as handle:
    failed = json.load(handle)
print(f"[pipeline] DONE: {scan[\"totalChecks\"]} total / {scan[\"failedChecks\"]} failed")
for item in failed:
    print(f"  FAIL  {item[\"checkId\"]}  {item[\"title\"]}")
' "$OUTPUT_DIR/scan.json" "$OUTPUT_DIR/failed-controls.json"
