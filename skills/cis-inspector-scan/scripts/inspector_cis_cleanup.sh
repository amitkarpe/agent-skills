#!/usr/bin/env bash
# inspector_cis_cleanup.sh
# Delete all Inspector CIS scan configurations targeting a given instance_id tag.
# Safe to run before any new scan to guarantee clean state.
set -euo pipefail

usage() {
  echo "Usage: $0 --profile <p> --region <r> --instance-id <i-xxx> [--dry-run]"
  exit 1
}

PROFILE="" REGION="" INSTANCE_ID="" DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)     PROFILE="$2";     shift 2 ;;
    --region)      REGION="$2";      shift 2 ;;
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true;     shift ;;
    *) usage ;;
  esac
done

[[ -z "$PROFILE" || -z "$REGION" || -z "$INSTANCE_ID" ]] && usage

log() { echo "[cleanup] $*"; }

EXISTING=$(aws --profile "$PROFILE" --region "$REGION" \
  inspector2 list-cis-scan-configurations --output json | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
arns = [c['scanConfigurationArn'] for c in data.get('scanConfigurations', [])
        if '$INSTANCE_ID' in c.get('targets', {}).get('targetResourceTags', {}).get('instance_id', [])]
print('\n'.join(arns))
" 2>/dev/null || true)

if [[ -z "$EXISTING" ]]; then
  log "No scan configs found for instance_id=$INSTANCE_ID"
  exit 0
fi

COUNT=0
while IFS= read -r ARN; do
  [[ -z "$ARN" ]] && continue
  if $DRY_RUN; then
    log "DRY-RUN would delete: $ARN"
  else
    aws --profile "$PROFILE" --region "$REGION" \
      inspector2 delete-cis-scan-configuration \
      --scan-configuration-arn "$ARN" >/dev/null 2>&1 && \
      log "Deleted: $ARN"
  fi
  COUNT=$((COUNT+1))
done <<< "$EXISTING"

if $DRY_RUN; then
  log "DRY-RUN: $COUNT config(s) would be deleted. Re-run without --dry-run to apply."
else
  log "Deleted $COUNT config(s). Waiting 15s for conflict to clear..."
  sleep 15
fi
