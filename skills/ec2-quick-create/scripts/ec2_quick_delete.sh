#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ec2_quick_delete.sh [--instance-ids <id1,id2>] [--all-active] [options]

Options:
  --instance-ids <id1,id2>   Comma-separated instance IDs
  --all-active               Use active skill-created instances from records
  --confirm <true|false>     Required for apply
  --region <aws-region>
  --apply                    Execute termination (default is plan-only)
  --plan                     Explicit plan-only
  -h, --help

Examples:
  ./ec2_quick_delete.sh --all-active --plan
  ./ec2_quick_delete.sh --instance-ids i-123,i-456 --confirm true --apply
USAGE
}

INSTANCE_IDS=""
ALL_ACTIVE="false"
CONFIRM="false"
MODE="plan"
REGION=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --instance-ids) INSTANCE_IDS="$2"; shift 2 ;;
    --all-active) ALL_ACTIVE="true"; shift ;;
    --confirm) CONFIRM="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --apply) MODE="apply"; shift ;;
    --plan) MODE="plan"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

AWS_ARGS=()
if [ -n "$REGION" ]; then
  AWS_ARGS+=(--region "$REGION")
fi

aws_cli() {
  aws "${AWS_ARGS[@]}" "$@"
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SKILL_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
RECORDS_DIR="$HOME/.AGENTS-temp/agent-skills/ec2-quick-create/records"
ACTIVE_FILE="$RECORDS_DIR/active.tsv"
HISTORY_FILE="$RECORDS_DIR/history.csv"

init_records() {
  mkdir -p "$RECORDS_DIR"
  if [ ! -f "$ACTIVE_FILE" ]; then
    printf "instance_id\tcreated_at\tstatus\tenv\tname\towner\tpurpose\trepo\tbranch\tregion\n" > "$ACTIVE_FILE"
  fi
  if [ ! -f "$HISTORY_FILE" ]; then
    printf "event,timestamp,instance_id,env,name,owner,purpose,repo,branch,region\n" > "$HISTORY_FILE"
  fi
}

trim_history() {
  if [ -f "$HISTORY_FILE" ]; then
    { head -n 1 "$HISTORY_FILE"; tail -n 50 "$HISTORY_FILE" | sed '1{/^event,/d}'; } > "$HISTORY_FILE.tmp"
    mv "$HISTORY_FILE.tmp" "$HISTORY_FILE"
  fi
}

list_active() {
  if [ -f "$ACTIVE_FILE" ]; then
    awk -F'\t' 'NR>1 && $3=="running" {printf " - %s | %s | %s | %s\n", $1, $2, $5, $6; n++; if (n>=10) exit}' "$ACTIVE_FILE"
  fi
}

active_ids() {
  if [ -f "$ACTIVE_FILE" ]; then
    awk -F'\t' 'NR>1 && $3=="running" {print $1}' "$ACTIVE_FILE" | paste -sd' ' -
  fi
}

record_terminated() {
  local instance_id="$1"
  local ts="$2"
  local row
  row=$(awk -F'\t' -v id="$instance_id" 'NR>1 && $1==id {print $0}' "$ACTIVE_FILE")

  local env="unknown" name="unknown" owner="unknown" purpose="unknown" repo="unknown" branch="unknown" region="unknown"
  if [ -n "$row" ]; then
    IFS=$'\t' read -r _ _ _ env name owner purpose repo branch region <<< "$row"
  fi

  printf "terminated,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
    "$ts" "$instance_id" "$env" "$name" "$owner" "$purpose" "$repo" "$branch" "$region" >> "$HISTORY_FILE"
  trim_history
}

remove_active_id() {
  local instance_id="$1"
  awk -F'\t' -v id="$instance_id" 'NR==1 || $1!=id' "$ACTIVE_FILE" > "$ACTIVE_FILE.tmp"
  mv "$ACTIVE_FILE.tmp" "$ACTIVE_FILE"
}

init_records

if [ "$ALL_ACTIVE" = "true" ]; then
  INSTANCE_IDS=$(active_ids || true)
fi

if [ -z "$INSTANCE_IDS" ]; then
  echo "No instance IDs provided. Active skill-created instances:"
  list_active
  exit 1
fi

IFS=',' read -r -a IDS_ARR <<< "$INSTANCE_IDS"

if [ "$MODE" = "plan" ]; then
  echo "Plan only. Instances to terminate: ${IDS_ARR[*]}"
  exit 0
fi

if [ "$CONFIRM" != "true" ]; then
  echo "Reconfirm with --confirm true before terminating." >&2
  exit 1
fi

aws_cli ec2 terminate-instances --instance-ids "${IDS_ARR[@]}" > /dev/null
aws_cli ec2 wait instance-terminated --instance-ids "${IDS_ARR[@]}"

ts_now="$(TZ=Asia/Singapore date '+%Y-%m-%dT%H:%M')SGT"
for id in "${IDS_ARR[@]}"; do
  remove_active_id "$id"
  record_terminated "$id" "$ts_now"
done

echo "Terminated: ${IDS_ARR[*]}"
