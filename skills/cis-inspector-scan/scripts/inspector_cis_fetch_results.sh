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

AWS="aws --profile $PROFILE --region $REGION"
mkdir -p "$OUTPUT_DIR"
log() { echo "[fetch-results] $*"; }

FILTER="{\"scanConfigurationArnFilters\":[{\"comparison\":\"EQUALS\",\"value\":\"$SCAN_CONFIG_ARN\"}]}"

# --- poll loop ---
SCAN_ARN=""
FINAL_STATUS=""
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_POLLS ]]; do
  ATTEMPT=$((ATTEMPT + 1))
  log "Poll $ATTEMPT/$MAX_POLLS — querying scan rows..."

  # Use --query JMESPath filter to avoid shell quoting issues with --filter-criteria JSON
  SCAN_LIST=$($AWS inspector2 list-cis-scans --output json 2>/dev/null || echo '{"scans":[]}')

  SCAN_ROW=$(echo "$SCAN_LIST" | python3 -c "
import sys,json
scans=json.load(sys.stdin).get('scans',[])
match=[s for s in scans if s.get('scanConfigurationArn')=='$SCAN_CONFIG_ARN']
print(json.dumps(match[0]) if match else '')
" 2>/dev/null || echo "")

  if [[ -z "$SCAN_ROW" ]]; then
    log "No scan row yet — waiting ${POLL_INTERVAL}s..."
    sleep "$POLL_INTERVAL"
    continue
  fi
  STATUS=$(echo "$SCAN_ROW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','UNKNOWN'))")
  TOTAL=$(echo "$SCAN_ROW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('totalChecks',0))")
  SCAN_ARN=$(echo "$SCAN_ROW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('scanArn',''))")

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
    PAGE_JSON=$($AWS inspector2 list-cis-scan-results-aggregated-by-checks \
      --scan-arn "$SCAN_ARN" \
      --next-token "$NEXT_TOKEN" \
      --output json)
  else
    PAGE_JSON=$($AWS inspector2 list-cis-scan-results-aggregated-by-checks \
      --scan-arn "$SCAN_ARN" \
      --output json)
  fi

  echo "$PAGE_JSON" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('checkAggregations',[])))" > "$TEMP_PAGE"
  python3 -c "import json; a=json.load(open('$TEMP_ALL')); b=json.load(open('$TEMP_PAGE')); json.dump(a+b, open('$TEMP_ALL','w'))"

  NEXT_TOKEN=$(echo "$PAGE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('nextToken',''))" 2>/dev/null || echo "")
  [[ -z "$NEXT_TOKEN" ]] && break
done

mv "$TEMP_ALL" "$OUTPUT_DIR/aggregated-checks.json"
rm -f "$TEMP_PAGE"

CHECK_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_DIR/aggregated-checks.json'))))")
log "Aggregated checks saved: $CHECK_COUNT checks → $OUTPUT_DIR/aggregated-checks.json"
log "scan.json saved → $OUTPUT_DIR/scan.json"
