#!/bin/bash
set -euo pipefail

CLUSTER=${1:?cluster}
PROFILE=${2:?profile}
REGION=${3:?region}
DURATION=${4:?duration_seconds}
INTERVAL=${5:?interval_seconds}
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_EPOCH=$(date +%s)

STAMP=$(date +%Y%m%d-%H%M%S)
OUT="${6:-$HOME/.AGENTS-temp/agent-skills/ecs-monitoring/watch-$STAMP}"
FOCUS_SERVICES_CSV=${7:-}
mkdir -p "$OUT"

echo "OUT_DIR=$OUT"
echo "CLUSTER=$CLUSTER"
echo "PROFILE=$PROFILE"
echo "REGION=$REGION"
echo "DURATION=$DURATION"
echo "INTERVAL=$INTERVAL"

mapfile -t SERVICES < <(
  aws --profile "$PROFILE" --region "$REGION" ecs list-services \
    --cluster "$CLUSTER" --output text --query 'serviceArns[]' |
    tr '\t' '\n' | awk -F/ '{print $NF}' | sort
)

printf '%s\n' "${SERVICES[@]}" > "$OUT/services.txt"
: > "$OUT/watch.log"

FOCUS_SERVICES=()
if [ -n "$FOCUS_SERVICES_CSV" ]; then
  mapfile -t FOCUS_SERVICES < <(printf '%s' "$FOCUS_SERVICES_CSV" | tr ',' '\n' | awk 'NF')
fi

ITERATIONS=$(( (DURATION + INTERVAL - 1) / INTERVAL ))
FLAP_SUMMARY_FILE="$OUT/flap-summary.txt"

for i in $(seq 1 "$ITERATIONS"); do
  TS=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$TS] watch $i/$ITERATIONS" | tee -a "$OUT/watch.log"

  for ((j=0; j<${#SERVICES[@]}; j+=10)); do
    batch=( "${SERVICES[@]:j:10}" )
    aws --profile "$PROFILE" --region "$REGION" ecs describe-services \
      --cluster "$CLUSTER" --services "${batch[@]}" > "$OUT/services-$i-$j.json"
    python3 - "$OUT/services-$i-$j.json" <<'PY' | tee -a "$OUT/watch.log"
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for svc in data["services"]:
    ev = svc.get("events", [{}])[0].get("message", "")
    print(
        f"SERVICE\t{svc['serviceName']}\tdesired={svc['desiredCount']}"
        f"\trunning={svc['runningCount']}\tpending={svc['pendingCount']}\t{ev[:160]}"
    )
PY
  done

  for svc in "${FOCUS_SERVICES[@]}"; do
    aws --profile "$PROFILE" --region "$REGION" ecs list-tasks \
      --cluster "$CLUSTER" --service-name "$svc" --desired-status RUNNING \
      > "$OUT/${svc}-running-$i.json"
    aws --profile "$PROFILE" --region "$REGION" ecs list-tasks \
      --cluster "$CLUSTER" --service-name "$svc" --desired-status STOPPED \
      > "$OUT/${svc}-stopped-$i.json"

    mapfile -t RUNNING < <(jaq -r '.taskArns[]?' "$OUT/${svc}-running-$i.json")
    mapfile -t STOPPED < <(jaq -r '.taskArns[]?' "$OUT/${svc}-stopped-$i.json" | head -n 4)

    if [ ${#RUNNING[@]} -gt 0 ]; then
      aws --profile "$PROFILE" --region "$REGION" ecs describe-tasks \
        --cluster "$CLUSTER" --tasks "${RUNNING[@]}" > "$OUT/${svc}-running-detail-$i.json"
      python3 - "$OUT/${svc}-running-detail-$i.json" "$svc" <<'PY' | tee -a "$OUT/watch.log"
import json, sys
path, svc = sys.argv[1:]
with open(path) as f:
    data = json.load(f)
for t in data["tasks"]:
    print(
        f"TASK\t{svc}\tRUNNING\t{t['taskArn'].split('/')[-1]}"
        f"\tlast={t.get('lastStatus')}\thealth={t.get('healthStatus')}"
    )
PY
    fi

    if [ ${#STOPPED[@]} -gt 0 ]; then
      aws --profile "$PROFILE" --region "$REGION" ecs describe-tasks \
        --cluster "$CLUSTER" --tasks "${STOPPED[@]}" > "$OUT/${svc}-stopped-detail-$i.json"
      python3 - "$OUT/${svc}-stopped-detail-$i.json" "$svc" <<'PY' | tee -a "$OUT/watch.log"
import json, sys
path, svc = sys.argv[1:]
with open(path) as f:
    data = json.load(f)
for t in data["tasks"][:4]:
    print(
        f"TASK\t{svc}\tSTOPPED\t{t['taskArn'].split('/')[-1]}"
        f"\tstopCode={t.get('stopCode','')}\treason={str(t.get('stoppedReason',''))[:160]}"
    )
PY
    fi
  done

  if [ "$i" -lt "$ITERATIONS" ]; then
    sleep "$INTERVAL"
  fi
done

echo '=== FLAP SUMMARY ===' | tee -a "$OUT/watch.log"
python3 - "$OUT/watch.log" <<'PY' | tee "$FLAP_SUMMARY_FILE" | tee -a "$OUT/watch.log"
import collections, re, sys
log = sys.argv[1]
svc_counts = collections.defaultdict(list)
stop_reasons = collections.defaultdict(list)
with open(log) as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if not parts:
            continue
        if parts[0] == "SERVICE":
            svc = parts[1]
            desired = int(re.search(r"desired=(\d+)", parts[2]).group(1))
            running = int(re.search(r"running=(\d+)", parts[3]).group(1))
            pending = int(re.search(r"pending=(\d+)", parts[4]).group(1))
            svc_counts[svc].append((desired, running, pending))
        elif parts[0] == "TASK" and parts[2] == "STOPPED":
            svc = parts[1]
            stop_reasons[svc].append(parts[4] + " " + parts[5])
for svc in sorted(svc_counts):
    vals = svc_counts[svc]
    unstable = any((r != d or p != 0) for d, r, p in vals)
    if unstable:
        print(f"{svc}\tUNSTABLE\t{vals}")
    else:
        print(f"{svc}\tSTEADY\t{vals[-1]}")
    if stop_reasons.get(svc):
        uniq = []
        for x in stop_reasons[svc]:
            if x not in uniq:
                uniq.append(x)
        for x in uniq[:5]:
            print(f"  STOP\t{x}")
PY

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
END_EPOCH=$(date +%s)
ELAPSED_SECONDS=$((END_EPOCH - START_EPOCH))

jq -n \
  --arg cluster "$CLUSTER" \
  --arg duration "$DURATION" \
  --arg interval "$INTERVAL" \
  --arg focus_services_csv "$FOCUS_SERVICES_CSV" \
  --arg start_ts "$START_TS" \
  --arg end_ts "$END_TS" \
  --argjson elapsed_seconds "$ELAPSED_SECONDS" \
  '{
    cluster: $cluster,
    duration_seconds: ($duration | tonumber),
    interval_seconds: ($interval | tonumber),
    focus_services_csv: $focus_services_csv,
    start_ts: $start_ts,
    end_ts: $end_ts,
    elapsed_seconds: $elapsed_seconds
  }' > "$OUT/timing.json"

{
  printf 'cluster=%s\n' "$CLUSTER"
  printf 'duration_seconds=%s\n' "$DURATION"
  printf 'interval_seconds=%s\n' "$INTERVAL"
  printf 'focus_services_csv=%s\n' "$FOCUS_SERVICES_CSV"
  printf 'start_ts=%s\n' "$START_TS"
  printf 'end_ts=%s\n' "$END_TS"
  printf 'elapsed_seconds=%s\n' "$ELAPSED_SECONDS"
  printf '\n=== FLAP SUMMARY ===\n'
  cat "$FLAP_SUMMARY_FILE"
} > "$OUT/summary.txt"
