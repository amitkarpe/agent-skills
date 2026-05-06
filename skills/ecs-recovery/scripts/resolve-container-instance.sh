#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <cluster> <profile> <region> <ec2_instance_id>" >&2
  exit 2
fi

CLUSTER="$1"
PROFILE="$2"
REGION="$3"
EC2_ID="$4"

aws --profile "$PROFILE" --region "$REGION" ecs list-container-instances \
  --cluster "$CLUSTER" \
  --status ACTIVE \
  --query 'containerInstanceArns[]' \
  --output text | tr '\t' '\n' | while read -r ARN; do
    [[ -z "$ARN" ]] && continue
    aws --profile "$PROFILE" --region "$REGION" ecs describe-container-instances \
      --cluster "$CLUSTER" \
      --container-instances "$ARN" \
      --query 'containerInstances[0].[ec2InstanceId,containerInstanceArn,status]' \
      --output text
  done | awk -v id="$EC2_ID" '$1==id {print $2; exit}'
