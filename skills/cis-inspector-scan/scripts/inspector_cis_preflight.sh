#!/usr/bin/env bash
# inspector_cis_preflight.sh
# Validate EC2 instance readiness for an Inspector CIS scan.
# Saves preflight.json to --output-dir on success.
# Exits non-zero on any failed check.
set -euo pipefail

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found (required for JSON parsing)"; exit 1; }

usage() {
  echo "Usage: $0 --profile <profile> --region <region> --instance-id <i-xxx> --output-dir <dir>"
  exit 1
}

PROFILE="" REGION="" INSTANCE_ID="" OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)      PROFILE="$2";      shift 2 ;;
    --region)       REGION="$2";       shift 2 ;;
    --instance-id)  INSTANCE_ID="$2";  shift 2 ;;
    --output-dir)   OUTPUT_DIR="$2";   shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$PROFILE" || -z "$REGION" || -z "$INSTANCE_ID" || -z "$OUTPUT_DIR" ]] && usage

AWS="aws --profile $PROFILE --region $REGION"
RESULT="{}"
FAIL=0

log()  { echo "[preflight] $*"; }
fail() { log "FAIL: $*"; FAIL=1; }
pass() { log "PASS: $*"; }

# --- output dir ---
mkdir -p "$OUTPUT_DIR"

# --- instance exists and is running ---
INSTANCE_JSON=$($AWS ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].{State:State.Name,InstanceId:InstanceId}' \
  --output json 2>/dev/null) || { fail "instance $INSTANCE_ID not found"; INSTANCE_JSON="{}"; }

INSTANCE_STATE=$(echo "$INSTANCE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('State','unknown'))" 2>/dev/null || echo "unknown")
if [[ "$INSTANCE_STATE" == "running" ]]; then
  pass "instance is running"
else
  fail "instance state is '$INSTANCE_STATE' (expected running)"
fi

# --- unique instance_id tag ---
TAG_VALUE=$($AWS ec2 describe-tags \
  --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=instance_id" \
  --query 'Tags[0].Value' --output text 2>/dev/null || echo "None")
if [[ "$TAG_VALUE" == "$INSTANCE_ID" ]]; then
  pass "unique tag instance_id=$INSTANCE_ID present"
else
  fail "tag instance_id=$INSTANCE_ID missing or wrong (got: $TAG_VALUE)"
fi

# --- InstanceMetadataTags enabled ---
META_TAGS=$($AWS ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].MetadataOptions.InstanceMetadataTags' \
  --output text 2>/dev/null || echo "unknown")
if [[ "$META_TAGS" == "enabled" ]]; then
  pass "InstanceMetadataTags=enabled"
else
  fail "InstanceMetadataTags=$META_TAGS (must be enabled)"
fi

# --- SSM managed ---
SSM_STATUS=$($AWS ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
  --query 'InstanceInformationList[0].PingStatus' \
  --output text 2>/dev/null || echo "None")
if [[ "$SSM_STATUS" == "Online" ]]; then
  pass "SSM managed (PingStatus=Online)"
else
  fail "SSM PingStatus=$SSM_STATUS (expected Online)"
fi

# --- AmazonInspector2ManagedCisPolicy on instance role ---
PROFILE_ARN=$($AWS ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' \
  --output text 2>/dev/null || echo "None")
IAM_CHECK="unknown"
if [[ "$PROFILE_ARN" != "None" && -n "$PROFILE_ARN" ]]; then
  PROFILE_NAME=$(echo "$PROFILE_ARN" | sed 's|.*/||')
  ROLE_NAME=$(aws --profile "$PROFILE" iam get-instance-profile \
    --instance-profile-name "$PROFILE_NAME" \
    --query 'InstanceProfile.Roles[0].RoleName' --output text 2>/dev/null || echo "")
  if [[ -n "$ROLE_NAME" ]]; then
    POLICIES=$(aws --profile "$PROFILE" iam list-attached-role-policies \
      --role-name "$ROLE_NAME" \
      --query 'AttachedPolicies[*].PolicyName' --output json 2>/dev/null || echo "[]")
    # Accept AmazonInspector2ManagedCisPolicy OR AmazonInspector2FullAccess_v2 (superset)
    HAS_POLICY=$(echo "$POLICIES" | python3 -c "
import sys,json
p=json.load(sys.stdin)
ok={'AmazonInspector2ManagedCisPolicy','AmazonInspector2FullAccess_v2','AmazonInspector2FullAccess'}
found=[x for x in p if x in ok]
print(found[0] if found else '')
" 2>/dev/null || echo "")
    if [[ -n "$HAS_POLICY" ]]; then
      IAM_CHECK="present"
      pass "Inspector CIS policy on role $ROLE_NAME ($HAS_POLICY)"
    else
      IAM_CHECK="missing"
      fail "No Inspector CIS policy on role $ROLE_NAME — need AmazonInspector2ManagedCisPolicy or AmazonInspector2FullAccess_v2"
    fi
  else
    IAM_CHECK="no-role"
    fail "Could not determine IAM role from instance profile $PROFILE_NAME"
  fi
else
  IAM_CHECK="no-profile"
  fail "No IAM instance profile attached — Inspector CIS scan requires AmazonInspector2ManagedCisPolicy"
fi

# --- save evidence ---
cat > "$OUTPUT_DIR/preflight.json" <<EOF
{
  "instance_id": "$INSTANCE_ID",
  "instance_state": "$INSTANCE_STATE",
  "instance_id_tag": "$TAG_VALUE",
  "instance_metadata_tags": "$META_TAGS",
  "ssm_ping_status": "$SSM_STATUS",
  "iam_cis_policy": "$IAM_CHECK",
  "preflight_passed": $([ $FAIL -eq 0 ] && echo true || echo false)
}
EOF

if [[ $FAIL -ne 0 ]]; then
  log "Preflight FAILED — fix issues above before creating a scan."
  log "Evidence saved to $OUTPUT_DIR/preflight.json"
  exit 1
fi

log "Preflight PASSED — evidence saved to $OUTPUT_DIR/preflight.json"
