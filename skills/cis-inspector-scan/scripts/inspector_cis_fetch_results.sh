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
#   aggregated-checks.json    full aggregated check results
set -euo pipefail

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found (required for JSON parsing)"; exit 1; }

valid_profile() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; }
valid_region() { [[ "$1" =~ ^[a-z]{2}(-gov)?-[a-z0-9-]+-[0-9]+$ ]]; }
valid_scan_config_arn() {
  [[ "$1" =~ ^arn:aws[a-zA-Z0-9-]*:inspector2:[a-z0-9-]+:[0-9]{12}:cis-scan-configuration/[A-Za-z0-9-]+$ ]]
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

# --- poll loop ---
SCAN_ARN=""
FINAL_STATUS=""
ATTEMPT=0
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
    log "Scan FAILED — raw row saved to $OUTPUT_DIR/scan.json"
    log "Check /var/log/amazon/inspector/scitor.log.* on the instance for plugin errors."
    exit 1
  fi

  if [[ "$STATUS" == "COMPLETED" ]]; then
    if [[ "$TOTAL" -eq 0 ]]; then
      echo "$SCAN_ROW" > "$OUTPUT_DIR/scan.json"
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
