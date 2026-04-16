#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 5 ]]; then
  echo "usage: $0 <cluster> <profile> <region> <since_timestamp> [output_dir]" >&2
  exit 2
fi

CLUSTER="$1"
PROFILE="$2"
REGION="$3"
SINCE_TS="$4"
OUTDIR="${5:-$HOME/.AGENTS-temp/agent-skills/awslogs-investigation/matrix-$(date +%Y%m%d-%H%M%S)}"

mkdir -p "$OUTDIR"

aws --profile "$PROFILE" --region "$REGION" ecs list-container-instances \
  --cluster "$CLUSTER" \
  --status ACTIVE \
  --output json > "$OUTDIR/container_instances_list.json"

mapfile -t ARNS < <(jq -r '.containerInstanceArns[]?' "$OUTDIR/container_instances_list.json")

if [[ ${#ARNS[@]} -eq 0 ]]; then
  echo "no active container instances found" >&2
  exit 1
fi

aws --profile "$PROFILE" --region "$REGION" ecs describe-container-instances \
  --cluster "$CLUSTER" \
  --container-instances "${ARNS[@]}" \
  --output json > "$OUTDIR/container_instances_full.json"

jq -r '.containerInstances[] | [.ec2InstanceId, .containerInstanceArn, .status, .runningTasksCount] | @tsv' \
  "$OUTDIR/container_instances_full.json" > "$OUTDIR/node-summary.tsv"

cut -f1 "$OUTDIR/node-summary.tsv" > "$OUTDIR/ec2_instances.txt"

while read -r INSTANCE; do
  [[ -z "$INSTANCE" ]] && continue
  bash "$(dirname "$0")/check-awslogs-node.sh" "$PROFILE" "$REGION" "$SINCE_TS" "$INSTANCE" \
    > "$OUTDIR/$INSTANCE.txt"
done < "$OUTDIR/ec2_instances.txt"

echo "$OUTDIR"
