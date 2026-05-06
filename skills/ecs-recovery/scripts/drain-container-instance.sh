#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 5 ]]; then
  echo "usage: $0 <cluster> <profile> <region> <ec2_instance_id> [output_dir]" >&2
  exit 2
fi

CLUSTER="$1"
PROFILE="$2"
REGION="$3"
EC2_ID="$4"
OUTDIR="${5:-$HOME/.AGENTS-temp/agent-skills/ecs-recovery/drain-$(date +%Y%m%d-%H%M%S)-${EC2_ID}}"

mkdir -p "$OUTDIR"

CI_ARN="$(bash "$(dirname "$0")/resolve-container-instance.sh" "$CLUSTER" "$PROFILE" "$REGION" "$EC2_ID")"

if [[ -z "$CI_ARN" ]]; then
  echo "container instance not found for $EC2_ID" >&2
  exit 1
fi

echo "$CI_ARN" > "$OUTDIR/container-instance-arn.txt"

aws --profile "$PROFILE" --region "$REGION" ecs update-container-instances-state \
  --cluster "$CLUSTER" \
  --container-instances "$CI_ARN" \
  --status DRAINING \
  --output json > "$OUTDIR/update-container-instance-state.json"

aws --profile "$PROFILE" --region "$REGION" ecs describe-container-instances \
  --cluster "$CLUSTER" \
  --container-instances "$CI_ARN" \
  --output json > "$OUTDIR/post-drain-container-instance.json"

cat "$OUTDIR/container-instance-arn.txt"
