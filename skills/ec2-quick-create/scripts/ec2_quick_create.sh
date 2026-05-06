#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ec2_quick_create.sh --env <dev|prod|account_id> --name <name> --owner-tag <owner> --purpose-tag <purpose> [options]

Required:
  --env
  --name
  --owner-tag
  --purpose-tag

Options:
  --instance-type <type>
  --subnet-id <subnet>
  --security-group-id <sg[,sg2]>
  --iam-instance-profile <profile_name>
  --volume-size-gb <size>          (fast defaults only)
  --key-name <key>
  --public-ip <true|false>
  --public-ip-confirm <true|false> (required if public IP true)
  --fast-defaults                  (use cached defaults)
  --region <aws-region>
  --task <task-tag>
  --apply                          (execute; default is plan-only)
  --plan                           (explicit plan-only)
  -h, --help

Examples:
  ./ec2_quick_create.sh --env dev --name jumpbox --owner-tag amit --purpose-tag ops --fast-defaults --apply
  ./ec2_quick_create.sh --env prod --name patcher --owner-tag amit --purpose-tag patching --subnet-id subnet-abc --security-group-id sg-123 --apply
USAGE
}

# Defaults
ENV=""
NAME=""
OWNER_TAG=""
PURPOSE_TAG=""
INSTANCE_TYPE=""
SUBNET_ID=""
SECURITY_GROUP_ID=""
IAM_INSTANCE_PROFILE="TerraformProductionAccessRole"
VOLUME_SIZE_GB=""
KEY_NAME=""
PUBLIC_IP="false"
PUBLIC_IP_CONFIRM="false"
FAST_DEFAULTS="false"
REGION=""
TASK=""
MODE="plan"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env) ENV="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --owner-tag) OWNER_TAG="$2"; shift 2 ;;
    --purpose-tag) PURPOSE_TAG="$2"; shift 2 ;;
    --instance-type) INSTANCE_TYPE="$2"; shift 2 ;;
    --subnet-id) SUBNET_ID="$2"; shift 2 ;;
    --security-group-id) SECURITY_GROUP_ID="$2"; shift 2 ;;
    --iam-instance-profile) IAM_INSTANCE_PROFILE="$2"; shift 2 ;;
    --volume-size-gb) VOLUME_SIZE_GB="$2"; shift 2 ;;
    --key-name) KEY_NAME="$2"; shift 2 ;;
    --public-ip) PUBLIC_IP="$2"; shift 2 ;;
    --public-ip-confirm) PUBLIC_IP_CONFIRM="$2"; shift 2 ;;
    --fast-defaults) FAST_DEFAULTS="true"; shift ;;
    --region) REGION="$2"; shift 2 ;;
    --task) TASK="$2"; shift 2 ;;
    --apply) MODE="apply"; shift ;;
    --plan) MODE="plan"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

if [ -z "$ENV" ] || [ -z "$NAME" ] || [ -z "$OWNER_TAG" ] || [ -z "$PURPOSE_TAG" ]; then
  echo "Missing required inputs." >&2
  usage
  exit 1
fi

if [ "$PUBLIC_IP" = "true" ] && [ "$PUBLIC_IP_CONFIRM" != "true" ]; then
  echo "Public IP requested. Reconfirm with --public-ip-confirm true." >&2
  exit 1
fi

if [ "$ENV" = "prod" ] && { [ -z "$SUBNET_ID" ] || [ -z "$SECURITY_GROUP_ID" ]; }; then
  echo "env=prod requires explicit --subnet-id and --security-group-id." >&2
  exit 1
fi

if [ -n "$VOLUME_SIZE_GB" ] && [ "$FAST_DEFAULTS" != "true" ]; then
  echo "--volume-size-gb override requires --fast-defaults to avoid altering baseline mappings." >&2
  exit 1
fi

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

warn_active_instances() {
  init_records
  local count
  count=$(awk -F'\t' 'NR>1 && $3=="running" {c++} END{print c+0}' "$ACTIVE_FILE")
  if [ "$count" -gt 0 ]; then
    echo "Warning: active skill-created instances from previous runs:"
    awk -F'\t' 'NR>1 && $3=="running" {printf " - %s | %s | %s | %s\n", $1, $2, $5, $6; n++; if (n>=10) exit}' "$ACTIVE_FILE"
    echo "Use scripts/ec2_quick_delete.sh to terminate."
  fi
}

get_repo_info() {
  local repo_root
  repo_root=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || true)
  if [ -z "$repo_root" ]; then
    repo_root=$(git -C "$SKILL_DIR/../.." rev-parse --show-toplevel 2>/dev/null || true)
  fi
  if [ -n "$repo_root" ]; then
    REPO_NAME=$(basename "$repo_root")
    BRANCH=$(git -C "$repo_root" rev-parse --abbrev-ref HEAD 2>/dev/null || true)
  fi
  if [ -z "${REPO_NAME:-}" ]; then
    REPO_NAME="unknown"
  fi
  if [ -z "${BRANCH:-}" ]; then
    BRANCH="unknown"
  fi
}

record_active() {
  local instance_id="$1"
  local created_at="$2"
  init_records
  awk -F'\t' -v id="$instance_id" 'NR==1 || $1!=id' "$ACTIVE_FILE" > "$ACTIVE_FILE.tmp"
  printf "%s\t%s\trunning\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$instance_id" "$created_at" "$ENV" "$NAME" "$OWNER_TAG" "$PURPOSE_TAG" "$REPO_NAME" "$BRANCH" "$EFFECTIVE_REGION" >> "$ACTIVE_FILE.tmp"
  mv "$ACTIVE_FILE.tmp" "$ACTIVE_FILE"
}

record_history() {
  local event="$1"
  local ts="$2"
  local instance_id="$3"
  init_records
  printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
    "$event" "$ts" "$instance_id" "$ENV" "$NAME" "$OWNER_TAG" "$PURPOSE_TAG" "$REPO_NAME" "$BRANCH" "$EFFECTIVE_REGION" >> "$HISTORY_FILE"
  trim_history
}

PROVISIONED_BY="skills-ec2-quick-create"
CREATED_AT="$(TZ=Asia/Singapore date '+%Y-%m-%dT%H:%M')SGT"
DEFAULT_REGION=$(aws configure get region 2>/dev/null || true)
EFFECTIVE_REGION="${REGION:-$DEFAULT_REGION}"
if [ -z "$EFFECTIVE_REGION" ]; then
  EFFECTIVE_REGION="unknown"
fi

get_repo_info
warn_active_instances

# Baseline constants
BASELINE_INSTANCE_ID="i-09f751985f7f639c4"
AMI_OWNER="148623356839"
AMI_NAME="GT_GCCS_StandardBuild_AML_2_on_2026-03-19_05.05.57"
AMI_ID="ami-026d0d206ed13f95c"
DEFAULT_INSTANCE_TYPE="t3.medium"
DEFAULT_SUBNET_ID="subnet-0d13ba2dcbb0f6d46"
DEFAULT_SECURITY_GROUP_ID="sg-0c8becd22fa808f6b"
DEFAULT_AZ="ap-southeast-1b"
DEFAULT_VOLUME_SIZE_GB="20"
DEFAULT_VOLUME_TYPE="gp3"
DEFAULT_IOPS="3000"
DEFAULT_THROUGHPUT="125"
DEFAULT_ENCRYPTED="false"
DEFAULT_DEVICE_NAME="/dev/xvda"

# AMI verification
AMI_CHECK=$(aws_cli ec2 describe-images \
  --image-ids "$AMI_ID" \
  --owners "$AMI_OWNER" \
  --query 'Images[0].ImageId' \
  --output text)

if [ -z "$AMI_CHECK" ] || [ "$AMI_CHECK" = "None" ]; then
  echo "AMI not found or owner mismatch: $AMI_ID (owner $AMI_OWNER)." >&2
  exit 1
fi

echo "AMI OK: $AMI_ID ($AMI_NAME)"

if [ -z "$INSTANCE_TYPE" ]; then
  INSTANCE_TYPE="$DEFAULT_INSTANCE_TYPE"
fi

METADATA_OPTIONS_ARG=()
MONITORING_ARG=()
EBS_OPTIMIZED_ARG=()
SHUTDOWN_BEHAVIOR_ARG=()
PLACEMENT_ARG=()
BLOCK_DEVICE_MAPPINGS=""
SG_IDS_CSV=""

if [ "$FAST_DEFAULTS" = "true" ]; then
  if [ -z "$SUBNET_ID" ]; then
    SUBNET_ID="$DEFAULT_SUBNET_ID"
  fi
  if [ -z "$SECURITY_GROUP_ID" ]; then
    SECURITY_GROUP_ID="$DEFAULT_SECURITY_GROUP_ID"
  fi
  SG_IDS_CSV=$(echo "$SECURITY_GROUP_ID" | tr -d ' ')
  FAST_AZ=$(aws_cli ec2 describe-subnets \
    --subnet-ids "$SUBNET_ID" \
    --query 'Subnets[0].AvailabilityZone' \
    --output text 2>/dev/null || true)
  if [ -z "$FAST_AZ" ] || [ "$FAST_AZ" = "None" ]; then
    FAST_AZ="$DEFAULT_AZ"
  fi
  PLACEMENT_ARG=(--placement "AvailabilityZone=$FAST_AZ")

  EFFECTIVE_VOLUME_SIZE="${VOLUME_SIZE_GB:-$DEFAULT_VOLUME_SIZE_GB}"
  BLOCK_DEVICE_MAPPINGS=$(printf '[{"DeviceName":"%s","Ebs":{"DeleteOnTermination":true,"VolumeType":"%s","VolumeSize":%s,"Iops":%s,"Throughput":%s,"Encrypted":%s}}]' \
    "$DEFAULT_DEVICE_NAME" \
    "$DEFAULT_VOLUME_TYPE" \
    "$EFFECTIVE_VOLUME_SIZE" \
    "$DEFAULT_IOPS" \
    "$DEFAULT_THROUGHPUT" \
    "$DEFAULT_ENCRYPTED")
else
  if [ -z "$SUBNET_ID" ]; then
    SUBNET_ID=$(aws_cli ec2 describe-instances \
      --instance-ids "$BASELINE_INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].SubnetId' \
      --output text)
  fi

  if [ -z "$SECURITY_GROUP_ID" ]; then
    SG_IDS_TEXT=$(aws_cli ec2 describe-instances \
      --instance-ids "$BASELINE_INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].SecurityGroups[].GroupId' \
      --output text)
    SG_IDS_CSV=$(echo "$SG_IDS_TEXT" | tr '\t ' ',')
  else
    SG_IDS_CSV=$(echo "$SECURITY_GROUP_ID" | tr -d ' ')
  fi

  AZ=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' \
    --output text)
  PLACEMENT_ARG=(--placement "AvailabilityZone=$AZ")

  TOKENS=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].MetadataOptions.HttpTokens' \
    --output text)
  ENDPOINT=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].MetadataOptions.HttpEndpoint' \
    --output text)
  HOP_LIMIT=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].MetadataOptions.HttpPutResponseHopLimit' \
    --output text)
  IPV6=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].MetadataOptions.HttpProtocolIpv6' \
    --output text)
  METADATA_OPTIONS_ARG=(--metadata-options "HttpTokens=$TOKENS,HttpEndpoint=$ENDPOINT,HttpPutResponseHopLimit=$HOP_LIMIT,HttpProtocolIpv6=$IPV6")

  MON_STATE=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].Monitoring.State' \
    --output text)
  if [ "$MON_STATE" = "enabled" ]; then
    MONITORING_ARG=(--monitoring "Enabled=true")
  fi

  EBS_OPT=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].EbsOptimized' \
    --output text)
  if [ "$EBS_OPT" = "True" ] || [ "$EBS_OPT" = "true" ]; then
    EBS_OPTIMIZED_ARG=(--ebs-optimized)
  fi

  SHUTDOWN_BEHAVIOR=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].InstanceInitiatedShutdownBehavior' \
    --output text)
  if [ -n "$SHUTDOWN_BEHAVIOR" ] && [ "$SHUTDOWN_BEHAVIOR" != "None" ]; then
    SHUTDOWN_BEHAVIOR_ARG=(--instance-initiated-shutdown-behavior "$SHUTDOWN_BEHAVIOR")
  fi

  BLOCK_DEVICE_MAPPINGS=$(aws_cli ec2 describe-instances \
    --instance-ids "$BASELINE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].BlockDeviceMappings[].{DeviceName:DeviceName,Ebs:{DeleteOnTermination:Ebs.DeleteOnTermination,VolumeType:Ebs.VolumeType,VolumeSize:Ebs.VolumeSize,Iops:Ebs.Iops,Throughput:Ebs.Throughput,Encrypted:Ebs.Encrypted}}' \
    --output json)
fi

ASSOC_PUBLIC_IP="false"
if [ "$PUBLIC_IP" = "true" ]; then
  ASSOC_PUBLIC_IP="true"
fi

NETWORK_INTERFACES="DeviceIndex=0,SubnetId=$SUBNET_ID,Groups=$SG_IDS_CSV,AssociatePublicIpAddress=$ASSOC_PUBLIC_IP"

TAGS="[{Key=Name,Value=$NAME},{Key=Env,Value=$ENV},{Key=Owner,Value=$OWNER_TAG},{Key=Purpose,Value=$PURPOSE_TAG},{Key=CreatedAt,Value=$CREATED_AT},{Key=Repo,Value=$REPO_NAME},{Key=Branch,Value=$BRANCH},{Key=ProvisionedBy,Value=$PROVISIONED_BY}]"
if [ -n "$TASK" ]; then
  TAGS="[{Key=Name,Value=$NAME},{Key=Env,Value=$ENV},{Key=Owner,Value=$OWNER_TAG},{Key=Purpose,Value=$PURPOSE_TAG},{Key=Task,Value=$TASK},{Key=CreatedAt,Value=$CREATED_AT},{Key=Repo,Value=$REPO_NAME},{Key=Branch,Value=$BRANCH},{Key=ProvisionedBy,Value=$PROVISIONED_BY}]"
fi

RUN_ARGS=(ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --iam-instance-profile "Name=$IAM_INSTANCE_PROFILE" \
  --network-interfaces "$NETWORK_INTERFACES" \
  --block-device-mappings "$BLOCK_DEVICE_MAPPINGS" \
  --tag-specifications "ResourceType=instance,Tags=$TAGS" \
  --query 'Instances[0].InstanceId' \
  --output text)

if [ -n "$KEY_NAME" ]; then
  RUN_ARGS+=(--key-name "$KEY_NAME")
fi

if [ "${#METADATA_OPTIONS_ARG[@]}" -gt 0 ]; then
  RUN_ARGS+=("${METADATA_OPTIONS_ARG[@]}")
fi

if [ "${#MONITORING_ARG[@]}" -gt 0 ]; then
  RUN_ARGS+=("${MONITORING_ARG[@]}")
fi

if [ "${#EBS_OPTIMIZED_ARG[@]}" -gt 0 ]; then
  RUN_ARGS+=("${EBS_OPTIMIZED_ARG[@]}")
fi

if [ "${#SHUTDOWN_BEHAVIOR_ARG[@]}" -gt 0 ]; then
  RUN_ARGS+=("${SHUTDOWN_BEHAVIOR_ARG[@]}")
fi

if [ "${#PLACEMENT_ARG[@]}" -gt 0 ]; then
  RUN_ARGS+=("${PLACEMENT_ARG[@]}")
fi

if [ "$MODE" = "plan" ]; then
  echo "Plan only. Command to run:"
  printf 'aws %s ' "${AWS_ARGS[@]}"
  printf '%q ' "${RUN_ARGS[@]}"
  echo
  exit 0
fi

INSTANCE_ID=$(aws_cli "${RUN_ARGS[@]}")

echo "InstanceId: $INSTANCE_ID"

aws_cli ec2 wait instance-running --instance-ids "$INSTANCE_ID"

aws_cli ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].{InstanceId:InstanceId,State:State.Name,PrivateIp:PrivateIpAddress,PublicIp:PublicIpAddress,SubnetId:SubnetId,VpcId:VpcId}' \
  --output table

aws_cli ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
  --query 'InstanceInformationList[0].{InstanceId:InstanceId,PingStatus:PingStatus,PlatformName:PlatformName,AgentVersion:AgentVersion}' \
  --output table

record_active "$INSTANCE_ID" "$CREATED_AT"
record_history "created" "$CREATED_AT" "$INSTANCE_ID"

echo "SSM connect: aws ${AWS_ARGS[*]} ssm start-session --target $INSTANCE_ID"
