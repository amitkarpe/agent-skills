#!/usr/bin/env bash
# inspector_cis_fetch_results.sh
# Poll for scan completion by scanConfigurationArn, then fetch aggregated checks.
#
# Exits non-zero if:
#   - scan status is FAILED
#   - scan completes with totalChecks = 0
#
# Outputs:
#   scan.json                 raw scan row
#   aggregated-targets.json   raw target aggregation on invalid scans, when available
#   target-status.json        concise per-target diagnosis on invalid scans
#   aggregated-checks.json    full aggregated check results
set -euo pipefail

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found (required for JSON parsing)"; exit 1; }

valid_profile() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; }
valid_region() { [[ "$1" =~ ^[a-z]{2}(-gov)?-[a-z0-9-]+-[0-9]+$ ]]; }
valid_scan_config_arn() {
  [[ "$1" =~ ^arn:aws(-us-gov|-cn)?:inspector2:[a-z]{2}(-gov)?-[a-z]+-[0-9]:[0-9]{12}:owner/([0-9]{12}|o-[a-z0-9]{10,32})/cis-configuration/[0-9a-fA-F-]+$ ]]
}
valid_positive_integer() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }

usage() {
  echo "Usage: $0 --profile <p> --region <r> --scan-config-arn <arn> --output-dir <dir>"
  exit 1
}

PROFILE="" REGION="" SCAN_CONFIG_ARN="" OUTPUT_DIR=""
POLL_INTERVAL=30
MAX_POLLS=10   # 10 * 30s = 5 min ceiling

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)          PROFILE="$2";          shift 2 ;;
    --region)           REGION="$2";           shift 2 ;;
    --scan-config-arn)  SCAN_CONFIG_ARN="$2";  shift 2 ;;
    --output-dir)       OUTPUT_DIR="$2";       shift 2 ;;
    --poll-interval)    POLL_INTERVAL="$2";    shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$PROFILE" || -z "$REGION" || -z "$SCAN_CONFIG_ARN" || -z "$OUTPUT_DIR" ]] && usage

valid_profile "$PROFILE" || { echo "ERROR: invalid profile" >&2; exit 2; }
valid_region "$REGION" || { echo "ERROR: invalid region" >&2; exit 2; }
valid_scan_config_arn "$SCAN_CONFIG_ARN" || { echo "ERROR: invalid scan configuration ARN" >&2; exit 2; }
valid_positive_integer "$POLL_INTERVAL" || { echo "ERROR: invalid poll interval" >&2; exit 2; }

AWS=(aws --profile "$PROFILE" --region "$REGION")
mkdir -p "$OUTPUT_DIR"
log() { echo "[fetch-results] $*"; }

save_target_aggregation() {
  [[ -n "$SCAN_ARN" ]] || return 0

  local target_json
  if target_json=$("${AWS[@]}" inspector2 list-cis-scan-results-aggregated-by-target-resource \
      --scan-arn "$SCAN_ARN" --output json 2>"$OUTPUT_DIR/aggregated-targets.stderr"); then
    printf '%s\n' "$target_json" > "$OUTPUT_DIR/aggregated-targets.json"
    if python3 - "$OUTPUT_DIR/aggregated-targets.json" "$OUTPUT_DIR/target-status.json" \
        2>"$OUTPUT_DIR/aggregated-targets.parse.stderr" <<'PY'
import json
import sys

source, destination = sys.argv[1:3]
with open(source) as handle:
    payload = json.load(handle)
rows = payload["targetResourceAggregations"]
if not isinstance(rows, list):
    raise ValueError("targetResourceAggregations must be a list")
statuses = [
    {
        "targetResourceId": row.get("targetResourceId"),
        "targetStatus": row.get("targetStatus", "UNKNOWN"),
        "targetStatusReason": row.get("targetStatusReason", "UNKNOWN"),
    }
    for row in rows
]
with open(destination, "w") as handle:
    json.dump({"targets": statuses}, handle)
    handle.write("\n")
PY
    then
      log "Target aggregation saved to $OUTPUT_DIR/aggregated-targets.json"
    else
      printf '%s\n' '{"targets":[],"diagnosticError":"TARGET_AGGREGATION_INVALID_RESPONSE"}' > "$OUTPUT_DIR/target-status.json"
      log "Target aggregation could not be parsed; raw response and error saved."
    fi
  else
    printf '%s\n' '{"targets":[],"diagnosticError":"TARGET_AGGREGATION_UNAVAILABLE"}' > "$OUTPUT_DIR/target-status.json"
    log "Target aggregation unavailable; error saved to $OUTPUT_DIR/aggregated-targets.stderr"
  fi
}

# --- poll loop ---
SCAN_ARN=""
FINAL_STATUS=""
ATTEMPT=0
STATUS="UNKNOWN"
TOTAL=0
while [[ $ATTEMPT -lt $MAX_POLLS ]]; do
  ATTEMPT=$((ATTEMPT + 1))
  log "Poll $ATTEMPT/$MAX_POLLS — querying scan rows..."

  # Use --query JMESPath filter to avoid shell quoting issues with --filter-criteria JSON
  SCAN_LIST=$("${AWS[@]}" inspector2 list-cis-scans --output json 2>/dev/null || echo '{"scans":[]}')

  SCAN_ROW=$(printf '%s' "$SCAN_LIST" | python3 -c '
import json, sys
scans = json.load(sys.stdin).get("scans", [])
match = [scan for scan in scans if scan.get("scanConfigurationArn") == sys.argv[1]]
print(json.dumps(match[0]) if match else "")
' "$SCAN_CONFIG_ARN" 2>/dev/null || echo "")

  if [[ -z "$SCAN_ROW" ]]; then
    log "No scan row yet — waiting ${POLL_INTERVAL}s..."
    sleep "$POLL_INTERVAL"
    continue
  fi
  STATUS=$(printf '%s' "$SCAN_ROW" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status","UNKNOWN"))')
  TOTAL=$(printf '%s' "$SCAN_ROW" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("totalChecks",0))')
  SCAN_ARN=$(printf '%s' "$SCAN_ROW" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("scanArn",""))')

  log "Status=$STATUS  totalChecks=$TOTAL  scanArn=$SCAN_ARN"

  if [[ "$STATUS" == "FAILED" ]]; then
    echo "$SCAN_ROW" > "$OUTPUT_DIR/scan.json"
    save_target_aggregation
    log "Scan FAILED — raw row saved to $OUTPUT_DIR/scan.json"
    log "Check /var/log/amazon/inspector/scitor.log.* on the instance for plugin errors."
    exit 1
  fi

  if [[ "$STATUS" == "COMPLETED" ]]; then
    if [[ "$TOTAL" -eq 0 ]]; then
      echo "$SCAN_ROW" > "$OUTPUT_DIR/scan.json"
      save_target_aggregation
      log "Scan COMPLETED but totalChecks=0 — result is not valid."
      log "Check: InstanceMetadataTags, IAM (AmazonInspector2ManagedCisPolicy), endpoints, accountIds."
      log "Raw row saved to $OUTPUT_DIR/scan.json"
      exit 1
    fi
    # valid result
    echo "$SCAN_ROW" > "$OUTPUT_DIR/scan.json"
    log "Scan COMPLETED with totalChecks=$TOTAL — valid result."
    FINAL_STATUS="COMPLETED"
    break
  fi

  log "Status=$STATUS — waiting ${POLL_INTERVAL}s..."
  sleep "$POLL_INTERVAL"
done

# Validate we exited with a valid completed scan
if [[ "$FINAL_STATUS" != "COMPLETED" ]]; then
  if [[ -n "$SCAN_ROW" ]]; then
    echo "$SCAN_ROW" > "$OUTPUT_DIR/scan.json"
    save_target_aggregation
  fi
  log "ERROR: Polling timed out or scan did not reach COMPLETED status."
  if [[ -n "$SCAN_ARN" ]]; then
    log "Last known status: $STATUS"
    log "Scan ARN: $SCAN_ARN"
  fi
  exit 1
fi

# --- fetch aggregated checks ---
log "Fetching aggregated checks for scanArn=$SCAN_ARN..."

TEMP_ALL="$OUTPUT_DIR/.all_checks.tmp"
TEMP_PAGE="$OUTPUT_DIR/.page_checks.tmp"
echo "[]" > "$TEMP_ALL"

NEXT_TOKEN=""
PAGE=0
while true; do
  PAGE=$((PAGE + 1))
  if [[ -n "$NEXT_TOKEN" ]]; then
    PAGE_JSON=$("${AWS[@]}" inspector2 list-cis-scan-results-aggregated-by-checks \
      --scan-arn "$SCAN_ARN" \
      --next-token "$NEXT_TOKEN" \
      --output json)
  else
    PAGE_JSON=$("${AWS[@]}" inspector2 list-cis-scan-results-aggregated-by-checks \
      --scan-arn "$SCAN_ARN" \
      --output json)
  fi

  printf '%s' "$PAGE_JSON" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin).get("checkAggregations",[])))' > "$TEMP_PAGE"
  python3 -c '
import json, sys
all_path, page_path = sys.argv[1:3]
with open(all_path) as handle:
    all_checks = json.load(handle)
with open(page_path) as handle:
    page_checks = json.load(handle)
with open(all_path, "w") as handle:
    json.dump(all_checks + page_checks, handle)
' "$TEMP_ALL" "$TEMP_PAGE"

  NEXT_TOKEN=$(printf '%s' "$PAGE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("nextToken",""))' 2>/dev/null || echo "")
  [[ -z "$NEXT_TOKEN" ]] && break
done

mv "$TEMP_ALL" "$OUTPUT_DIR/aggregated-checks.json"
rm -f "$TEMP_PAGE"

CHECK_COUNT=$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$OUTPUT_DIR/aggregated-checks.json")
log "Aggregated checks saved: $CHECK_COUNT checks → $OUTPUT_DIR/aggregated-checks.json"
log "scan.json saved → $OUTPUT_DIR/scan.json"
