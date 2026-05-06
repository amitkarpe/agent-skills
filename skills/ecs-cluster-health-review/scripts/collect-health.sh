#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "usage: $0 <cluster> <profile> <region> [output_dir]" >&2
  exit 2
fi

CLUSTER="$1"
PROFILE="$2"
REGION="$3"
OUTDIR="${4:-$HOME/.AGENTS-temp/agent-skills/ecs-cluster-health-review/$(date -u +%Y%m%dT%H%M%SZ)}"

mkdir -p "$OUTDIR"

AWS=(aws --profile "$PROFILE" --region "$REGION")

if [[ -x /home/dev/.local/bin/rtk ]]; then
  /home/dev/.local/bin/rtk aws --profile "$PROFILE" --region "$REGION" \
    ecs describe-clusters --clusters "$CLUSTER" --include STATISTICS \
    > "$OUTDIR/rtk-cluster.txt" || true
fi

"${AWS[@]}" ecs describe-clusters \
  --clusters "$CLUSTER" \
  --include STATISTICS \
  > "$OUTDIR/cluster.json"

"${AWS[@]}" ecs list-services \
  --cluster "$CLUSTER" \
  > "$OUTDIR/services-list.json"

mapfile -t SERVICES < <(jq -r '.serviceArns[]?' "$OUTDIR/services-list.json")

if [[ ${#SERVICES[@]} -gt 0 ]]; then
  for ((i=0; i<${#SERVICES[@]}; i+=10)); do
    batch=("${SERVICES[@]:i:10}")
    "${AWS[@]}" ecs describe-services \
      --cluster "$CLUSTER" \
      --services "${batch[@]}" \
      > "$OUTDIR/services-batch-$i.json"
  done
  jq -s '{services: map(.services[]) }' "$OUTDIR"/services-batch-*.json \
    > "$OUTDIR/services.json"
else
  printf '{"services":[]}\n' > "$OUTDIR/services.json"
fi

jq -r '.services[]
  | [.serviceName, .status, .desiredCount, .runningCount, .pendingCount]
  | @tsv' "$OUTDIR/services.json" > "$OUTDIR/service-summary.tsv"

jq -r '.services[]
  | select(.status != "ACTIVE" or .desiredCount != .runningCount or .pendingCount != 0)
  | [.serviceName, .status, .desiredCount, .runningCount, .pendingCount]
  | @tsv' "$OUTDIR/services.json" > "$OUTDIR/non-steady-services.tsv"

"${AWS[@]}" ecs list-container-instances \
  --cluster "$CLUSTER" \
  --status ACTIVE \
  > "$OUTDIR/container-instances-active-list.json"

"${AWS[@]}" ecs list-container-instances \
  --cluster "$CLUSTER" \
  --status DRAINING \
  > "$OUTDIR/container-instances-draining-list.json"

mapfile -t ACTIVE_CIS < <(jq -r '.containerInstanceArns[]?' "$OUTDIR/container-instances-active-list.json")
if [[ ${#ACTIVE_CIS[@]} -gt 0 ]]; then
  "${AWS[@]}" ecs describe-container-instances \
    --cluster "$CLUSTER" \
    --container-instances "${ACTIVE_CIS[@]}" \
    > "$OUTDIR/container-instances-active.json"
else
  printf '{"containerInstances":[]}\n' > "$OUTDIR/container-instances-active.json"
fi

mapfile -t DRAINING_CIS < <(jq -r '.containerInstanceArns[]?' "$OUTDIR/container-instances-draining-list.json")
if [[ ${#DRAINING_CIS[@]} -gt 0 ]]; then
  "${AWS[@]}" ecs describe-container-instances \
    --cluster "$CLUSTER" \
    --container-instances "${DRAINING_CIS[@]}" \
    > "$OUTDIR/container-instances-draining.json"
else
  printf '{"containerInstances":[]}\n' > "$OUTDIR/container-instances-draining.json"
fi

jq -r '.containerInstances[]
  | [
      .ec2InstanceId,
      .status,
      .runningTasksCount,
      .pendingTasksCount,
      .agentConnected,
      (([.attributes[]? | select(.name == "ami_lane") | .value][0]) // "stable-or-unset")
    ]
  | @tsv' "$OUTDIR/container-instances-active.json" > "$OUTDIR/active-node-summary.tsv"

jq -r '.containerInstances[]
  | [
      .ec2InstanceId,
      .status,
      .runningTasksCount,
      .pendingTasksCount,
      .agentConnected,
      (([.attributes[]? | select(.name == "ami_lane") | .value][0]) // "stable-or-unset")
    ]
  | @tsv' "$OUTDIR/container-instances-draining.json" > "$OUTDIR/draining-node-summary.tsv"

REGISTERED="$(jq -r '.clusters[0].registeredContainerInstancesCount // 0' "$OUTDIR/cluster.json")"
RUNNING_TASKS="$(jq -r '.clusters[0].runningTasksCount // 0' "$OUTDIR/cluster.json")"
PENDING_TASKS="$(jq -r '.clusters[0].pendingTasksCount // 0' "$OUTDIR/cluster.json")"
ACTIVE_SERVICES="$(jq -r '.clusters[0].activeServicesCount // 0' "$OUTDIR/cluster.json")"
SERVICE_COUNT="$(jq -r '.services | length' "$OUTDIR/services.json")"
NON_STEADY_COUNT="$(wc -l < "$OUTDIR/non-steady-services.tsv" | tr -d ' ')"
ACTIVE_NODE_COUNT="$(wc -l < "$OUTDIR/active-node-summary.tsv" | tr -d ' ')"
DRAINING_NODE_COUNT="$(wc -l < "$OUTDIR/draining-node-summary.tsv" | tr -d ' ')"

{
  printf '# ECS Cluster Health Review\n\n'
  printf -- '- Cluster: `%s`\n' "$CLUSTER"
  printf -- '- Profile: `%s`\n' "$PROFILE"
  printf -- '- Region: `%s`\n' "$REGION"
  printf -- '- Captured: `%s`\n\n' "$(date -Iseconds)"
  printf '## Summary\n\n'
  printf -- '- Registered container instances: `%s`\n' "$REGISTERED"
  printf -- '- Active container instances: `%s`\n' "$ACTIVE_NODE_COUNT"
  printf -- '- Draining container instances: `%s`\n' "$DRAINING_NODE_COUNT"
  printf -- '- Active services: `%s`\n' "$ACTIVE_SERVICES"
  printf -- '- Described services: `%s`\n' "$SERVICE_COUNT"
  printf -- '- Running tasks: `%s`\n' "$RUNNING_TASKS"
  printf -- '- Pending tasks: `%s`\n' "$PENDING_TASKS"
  printf -- '- Non-steady services: `%s`\n\n' "$NON_STEADY_COUNT"
  printf '## Non-Steady Services\n\n'
  if [[ "$NON_STEADY_COUNT" == "0" ]]; then
    printf -- '- None\n\n'
  else
    printf '```tsv\nservice\tstatus\tdesired\trunning\tpending\n'
    cat "$OUTDIR/non-steady-services.tsv"
    printf '```\n\n'
  fi
  printf '## Draining Nodes\n\n'
  if [[ "$DRAINING_NODE_COUNT" == "0" ]]; then
    printf -- '- None\n\n'
  else
    printf '```tsv\nec2\tstatus\trunning_tasks\tpending_tasks\tagent_connected\tami_lane\n'
    cat "$OUTDIR/draining-node-summary.tsv"
    printf '```\n\n'
  fi
  printf '## Evidence\n\n'
  printf -- '- `%s`\n' "$OUTDIR"
} > "$OUTDIR/summary.md"

printf '%s\n' "$OUTDIR"
