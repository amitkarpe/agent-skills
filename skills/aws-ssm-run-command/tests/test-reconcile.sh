#!/usr/bin/env bash
set -euo pipefail

skill_dir="$(cd "$(dirname "$0")/.." && pwd)"
repo_dir="$(cd "$skill_dir/../.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT

export AWS_MOCK_CALLS="$test_dir/aws-calls"
export AWS_MOCK_STATUS=Success
export AWS_MOCK_PING=Online
command_id=11111111-1111-1111-1111-111111111111

aws() {
  while [[ "$1" == --region || "$1" == --profile ]]; do shift 2; done
  case "$1/$2" in
    sts/get-caller-identity) printf '{"Account":"123456789012"}\n' ;;
    ssm/describe-instance-information) printf '{"InstanceInformationList":[{"PingStatus":"%s"}]}\n' "$AWS_MOCK_PING" ;;
    ssm/send-command)
      printf 'send\n' >> "$AWS_MOCK_CALLS"
      printf '11111111-1111-1111-1111-111111111111\n'
      ;;
    ssm/get-command-invocation)
      printf 'get\n' >> "$AWS_MOCK_CALLS"
      printf '{"Status":"%s","ResponseCode":0,"ExecutionStartDateTime":null,"ExecutionEndDateTime":null,"StdOut":"ok","StdErr":""}\n' "$AWS_MOCK_STATUS"
      ;;
    *) printf 'unexpected AWS call: %s %s\n' "$1" "$2" >&2; return 9 ;;
  esac
}
export -f aws

printf 'true\n' > "$test_dir/commands.sh"
core_args=(--region ap-southeast-1 --instance-id i-abc --comment test
  --commands-file "$test_dir/commands.sh" --command-id-file "$test_dir/command-id.txt"
  --poll-seconds 1 --max-wait-seconds 1)

# No prior execution: one send, then durable ID and exact-ID readback.
"$skill_dir/scripts/ssm_run.sh" "${core_args[@]}" > "$test_dir/result.json"
[[ "$(<"$test_dir/command-id.txt")" == "$command_id" ]]
[[ "$(jq -r '.Wait.Status' "$test_dir/result.json")" == Success ]]
[[ "$(grep -c '^send$' "$AWS_MOCK_CALLS")" == 1 ]]

# Completed prior execution: read back, never send a second command.
"$skill_dir/scripts/ssm_run.sh" "${core_args[@]}" > "$test_dir/result.json"
[[ "$(grep -c '^send$' "$AWS_MOCK_CALLS")" == 1 ]]
[[ "$(jq -r '.Wait.Status' "$test_dir/result.json")" == Success ]]

# Existing ID still running: wait/timeout on that ID, never resend.
export AWS_MOCK_STATUS=InProgress
if "$skill_dir/scripts/ssm_run.sh" "${core_args[@]}" > "$test_dir/result.json" 2> "$test_dir/error"; then
  echo 'running command unexpectedly passed' >&2; exit 1
fi
[[ "$(grep -c '^send$' "$AWS_MOCK_CALLS")" == 1 ]]
[[ "$(jq -r '.Wait.Status' "$test_dir/result.json")" == TimedOut ]]

# Unknown send outcome: fail closed before any provider call.
printf 'PENDING\n' > "$test_dir/command-id.txt"
before="$(wc -l < "$AWS_MOCK_CALLS")"
if "$skill_dir/scripts/ssm_run.sh" "${core_args[@]}" > "$test_dir/result.json" 2> "$test_dir/error"; then
  echo 'unknown command outcome unexpectedly passed' >&2; exit 1
fi
[[ "$(wc -l < "$AWS_MOCK_CALLS")" == "$before" ]]

# Evidence wrapper's document path also reuses the recorded CommandId.
export AWS_MOCK_STATUS=Success
printf '{}\n' > "$test_dir/parameters.json"
wrapper_args=(--instance-id i-abc --region ap-southeast-1
  --output-dir "$test_dir/document-run" --document-name TestDocument
  --parameters-file "$test_dir/parameters.json" --poll-seconds 1)
"$repo_dir/skills/ssm-command-evidence/scripts/run.sh" "${wrapper_args[@]}" > /dev/null
export AWS_MOCK_PING=Offline
"$repo_dir/skills/ssm-command-evidence/scripts/run.sh" "${wrapper_args[@]}" > /dev/null
[[ "$(grep -c '^send$' "$AWS_MOCK_CALLS")" == 2 ]]
[[ "$(<"$test_dir/document-run/command-id.txt")" == "$command_id" ]]

printf 'PENDING\n' > "$test_dir/document-run/command-id.txt"
before="$(wc -l < "$AWS_MOCK_CALLS")"
if "$repo_dir/skills/ssm-command-evidence/scripts/run.sh" "${wrapper_args[@]}" > /dev/null 2> "$test_dir/error"; then
  echo 'unknown document outcome unexpectedly passed' >&2; exit 1
fi
[[ "$(wc -l < "$AWS_MOCK_CALLS")" == "$before" ]]

echo 'SSM reconcile-before-repeat: PASS'
