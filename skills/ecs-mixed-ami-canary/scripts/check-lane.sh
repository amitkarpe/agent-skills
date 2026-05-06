#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  check-lane.sh <cluster> <profile> <region> <stable_service> <canary_service> [output_dir]
EOF
  exit 1
}

[[ $# -lt 5 ]] && usage

CLUSTER=${1:?cluster}
PROFILE=${2:?profile}
REGION=${3:?region}
STABLE_SERVICE=${4:?stable_service}
CANA_SERVICE=${5:?canary_service}
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_EPOCH=$(date +%s)
STAMP=$(date +%Y%m%d-%H%M%S)
OUT=${6:-"$HOME/.AGENTS-temp/agent-skills/ecs-mixed-ami-canary/$STAMP"}
mkdir -p "$OUT"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" | tee -a "$OUT/run.log"; }

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing dependency: $1" >&2
    exit 1
  }
}

need aws
need jq
need python3

AWS=(aws --profile "$PROFILE" --region "$REGION")

log "OUT_DIR=$OUT"
log "cluster=$CLUSTER stable_service=$STABLE_SERVICE canary_service=$CANA_SERVICE"

"${AWS[@]}" ecs describe-clusters \
  --clusters "$CLUSTER" \
  --include ATTACHMENTS CONFIGURATIONS SETTINGS STATISTICS TAGS \
  > "$OUT/cluster.json"

"${AWS[@]}" ecs list-container-instances \
  --cluster "$CLUSTER" \
  > "$OUT/container-instances.json"

mapfile -t CONTAINER_INSTANCE_ARNS < <(jq -r '.containerInstanceArns[]?' "$OUT/container-instances.json")

if [[ ${#CONTAINER_INSTANCE_ARNS[@]} -gt 0 ]]; then
  "${AWS[@]}" ecs describe-container-instances \
    --cluster "$CLUSTER" \
    --container-instances "${CONTAINER_INSTANCE_ARNS[@]}" \
    --include TAGS CONTAINER_INSTANCE_HEALTH \
    > "$OUT/container-instance-detail.json"
else
  printf '{"containerInstances":[]}\n' > "$OUT/container-instance-detail.json"
fi

"${AWS[@]}" ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$STABLE_SERVICE" "$CANA_SERVICE" \
  > "$OUT/services.json"

mapfile -t TASK_ARNS < <(
  jq -r '.services[]?.deployments[]?.taskSets[]? | empty' "$OUT/services.json" 2>/dev/null || true
)

mapfile -t RUNNING_TASK_ARNS < <(
  for svc in "$STABLE_SERVICE" "$CANA_SERVICE"; do
    "${AWS[@]}" ecs list-tasks --cluster "$CLUSTER" --service-name "$svc" --desired-status RUNNING \
      | jq -r '.taskArns[]?'
  done | sort -u
)

if [[ ${#RUNNING_TASK_ARNS[@]} -gt 0 ]]; then
  "${AWS[@]}" ecs describe-tasks \
    --cluster "$CLUSTER" \
    --tasks "${RUNNING_TASK_ARNS[@]}" \
    > "$OUT/tasks.json"
else
  printf '{"tasks":[]}\n' > "$OUT/tasks.json"
fi

python3 - "$OUT/container-instance-detail.json" "$OUT/tasks.json" <<'PY' > "$OUT/ec2-instance-ids.txt"
import json, sys
container_path, tasks_path = sys.argv[1:]
ids = set()
with open(container_path) as f:
    for item in json.load(f).get("containerInstances", []):
        ec2 = item.get("ec2InstanceId")
        if ec2:
            ids.add(ec2)
with open(tasks_path) as f:
    for task in json.load(f).get("tasks", []):
        for att in task.get("attachments", []):
            for detail in att.get("details", []):
                if detail.get("name") == "containerInstanceArn":
                    pass
for i in sorted(ids):
    print(i)
PY

if [[ -s "$OUT/ec2-instance-ids.txt" ]]; then
  mapfile -t EC2_IDS < "$OUT/ec2-instance-ids.txt"
  "${AWS[@]}" ec2 describe-instances \
    --instance-ids "${EC2_IDS[@]}" \
    > "$OUT/ec2-instances.json"

  "${AWS[@]}" autoscaling describe-auto-scaling-instances \
    --instance-ids "${EC2_IDS[@]}" \
    > "$OUT/asg-instance-map.json"
else
  printf '{"Reservations":[]}\n' > "$OUT/ec2-instances.json"
  printf '{"AutoScalingInstances":[]}\n' > "$OUT/asg-instance-map.json"
fi

python3 - "$OUT/services.json" "$OUT/container-instance-detail.json" "$OUT/ec2-instances.json" "$OUT/asg-instance-map.json" <<'PY' | tee "$OUT/summary.txt"
import json, sys
services_path, cis_path, ec2_path, asg_path = sys.argv[1:]

with open(services_path) as f:
    services = json.load(f).get("services", [])
with open(cis_path) as f:
    container_instances = json.load(f).get("containerInstances", [])
with open(ec2_path) as f:
    reservations = json.load(f).get("Reservations", [])
with open(asg_path) as f:
    asg_map = {x["InstanceId"]: x.get("AutoScalingGroupName","") for x in json.load(f).get("AutoScalingInstances", [])}

ci_map = {}
for ci in container_instances:
    attrs = {a["name"]: a.get("value","") for a in ci.get("attributes", [])}
    ci_map[ci.get("ec2InstanceId")] = {
        "status": ci.get("status"),
        "agentConnected": ci.get("agentConnected"),
        "attributes": attrs,
    }

instances = []
for res in reservations:
    for inst in res.get("Instances", []):
        iid = inst["InstanceId"]
        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
        instances.append({
            "id": iid,
            "ami": inst.get("ImageId",""),
            "lt": inst.get("LaunchTemplate", {}).get("LaunchTemplateName",""),
            "ltv": inst.get("LaunchTemplate", {}).get("Version",""),
            "asg": asg_map.get(iid, ""),
            "ami_lane": ci_map.get(iid, {}).get("attributes", {}).get("ami_lane",""),
            "ecs_status": ci_map.get(iid, {}).get("status",""),
            "agent_connected": ci_map.get(iid, {}).get("agentConnected",""),
            "name": tags.get("Name",""),
        })

print("=== SERVICES ===")
for svc in services:
    cps = ",".join(f"{x.get('capacityProvider')}:{x.get('weight',0)}" for x in svc.get("capacityProviderStrategy", [])) or "-"
    placement = ",".join(
        f"{x.get('type')}:{x.get('field')}" if x.get("field") else x.get("type","")
        for x in svc.get("placementConstraints", []) + svc.get("placementStrategy", [])
    ) or "-"
    print(f"{svc['serviceName']}\tdesired={svc.get('desiredCount')}\trunning={svc.get('runningCount')}\tcp={cps}\tplacement={placement}")

print("=== INSTANCES ===")
for inst in sorted(instances, key=lambda x: (x["ami_lane"], x["id"])):
    print(
        f"{inst['id']}\tami={inst['ami']}\tasg={inst['asg'] or '-'}\tlt={inst['lt'] or '-'}"
        f"\tlane={inst['ami_lane'] or '-'}\tecs={inst['ecs_status']}\tagent={inst['agent_connected']}"
    )
PY

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
END_EPOCH=$(date +%s)
ELAPSED_SECONDS=$((END_EPOCH - START_EPOCH))

jq -n \
  --arg cluster "$CLUSTER" \
  --arg stable_service "$STABLE_SERVICE" \
  --arg canary_service "$CANA_SERVICE" \
  --arg start_ts "$START_TS" \
  --arg end_ts "$END_TS" \
  --argjson elapsed_seconds "$ELAPSED_SECONDS" \
  '{
    cluster: $cluster,
    stable_service: $stable_service,
    canary_service: $canary_service,
    start_ts: $start_ts,
    end_ts: $end_ts,
    elapsed_seconds: $elapsed_seconds
  }' > "$OUT/timing.json"

cat > "$OUT/timing.txt" <<EOF
cluster=$CLUSTER
stable_service=$STABLE_SERVICE
canary_service=$CANA_SERVICE
start_ts=$START_TS
end_ts=$END_TS
elapsed_seconds=$ELAPSED_SECONDS
EOF

log "saved evidence to $OUT"
