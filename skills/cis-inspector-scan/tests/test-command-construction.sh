#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"
config_arn="arn:aws:inspector2:ap-southeast-1:123456789012:owner/123456789012/cis-configuration/5994f86b-4be0-4877-b5ce-e8fedfbed316"
org_config_arn="arn:aws:inspector2:ap-southeast-1:123456789012:owner/o-exampleorg1/cis-configuration/5994f86b-4be0-4877-b5ce-e8fedfbed316"
scan_arn="arn:aws:inspector2:ap-southeast-1:123456789012:owner/123456789012/cis-scan/5994f86b-4be0-4877-b5ce-e8fedfbed316"
export FAKE_AWS_CALLS="$tmp/calls.log"
export FAKE_TARGETS="$tmp/targets.jsonl"
export FAKE_CONFIG_ARN="$config_arn"
export FAKE_SCAN_ARN="$scan_arn"
export FAKE_SCAN_MODE=healthy
export FAKE_TARGET_AGG_MODE=healthy
: > "$FAKE_AWS_CALLS"
: > "$FAKE_TARGETS"

cat > "$tmp/bin/aws" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%q ' "$@" >> "$FAKE_AWS_CALLS"
printf '\n' >> "$FAKE_AWS_CALLS"
for ((i=1; i <= $#; i++)); do
  if [[ "${!i}" == "--targets" ]]; then
    j=$((i + 1))
    printf '%s' "${!j}" | python3 -m json.tool >/dev/null
    printf '%s\n' "${!j}" >> "$FAKE_TARGETS"
  fi
done
case " $* " in
  *" inspector2 list-cis-scans "*)
    case "$FAKE_SCAN_MODE" in
      failed) status=FAILED; checks=0 ;;
      zero) status=COMPLETED; checks=0 ;;
      timeout) status=IN_PROGRESS; checks=0 ;;
      *) status=COMPLETED; checks=1 ;;
    esac
    printf '{"scans":[{"scanConfigurationArn":"%s","scanArn":"%s","status":"%s","totalChecks":%s}]}\n' "$FAKE_CONFIG_ARN" "$FAKE_SCAN_ARN" "$status" "$checks"
    ;;
  *" inspector2 list-cis-scan-results-aggregated-by-target-resource "*)
    case "$FAKE_TARGET_AGG_MODE" in
      unavailable) echo 'diagnostic API unavailable' >&2; exit 1 ;;
      invalid) echo 'invalid JSON'; exit 0 ;;
    esac
    printf '%s\n' '{"targetResourceAggregations":[{"targetResourceId":"i-0123456789abcdef0","targetStatus":"TIMED_OUT","targetStatusReason":"SCAN_IN_PROGRESS"},{"targetResourceId":"i-0fedcba9876543210","targetStatus":"CANCELLED","targetStatusReason":"SSM_UNMANAGED"}]}'
    ;;
  *" inspector2 list-cis-scan-results-aggregated-by-checks "*) printf '{"checkAggregations":[{"checkId":"1","statusCounts":{"failed":0}}]}\n' ;;
  *" inspector2 create-cis-scan-configuration "*) printf '{"scanConfigurationArn":"%s"}\n' "$FAKE_CONFIG_ARN" ;;
  *" inspector2 list-cis-scan-configurations "*)
    count_file="${FAKE_AWS_CALLS}.configs"
    count=0
    [[ -f "$count_file" ]] && count="$(cat "$count_file")"
    count=$((count + 1))
    printf '%s' "$count" > "$count_file"
    if [[ "$count" -eq 1 ]]; then
      printf '{"scanConfigurations":[]}\n'
    else
      printf '{"scanConfigurations":[{"scanConfigurationArn":"%s","targets":{"targetResourceTags":{"instance_id":["i-0123456789abcdef0"]}}}]}\n' "$FAKE_CONFIG_ARN"
    fi
    ;;
  *" inspector2 delete-cis-scan-configuration "*) echo "unexpected delete" >&2; exit 1 ;;
  *) echo "unexpected fake aws arguments: $*" >&2; exit 1 ;;
esac
EOF
chmod +x "$tmp/bin/aws"
export PATH="$tmp/bin:$PATH"
run_bash() { env -u BASH_ENV PATH="$PATH" /bin/bash "$@"; }
expected_aws="$tmp/bin/aws"
assert_fake_aws() { run_bash -c 'test "$(command -v aws)" = "$1"' bash "$expected_aws"; }
assert_fake_aws

fetch="$repo/skills/cis-inspector-scan/scripts/inspector_cis_fetch_results.sh"
create="$repo/skills/cis-inspector-scan/scripts/inspector_cis_create_or_recover_scan.sh"
pipeline="$repo/skills/cis-inspector-scan/scripts/inspector_cis_full_pipeline.sh"
out_fetch="$tmp/output space ' quote"
out_create="$tmp/create space ' quote"

run_bash "$fetch" --profile dev --region ap-southeast-1 --scan-config-arn "$config_arn" --output-dir "$out_fetch" --poll-interval 1 >/dev/null
python3 -m json.tool "$out_fetch/scan.json" >/dev/null
python3 -m json.tool "$out_fetch/aggregated-checks.json" >/dev/null

# Invalid scans keep per-target diagnoses without turning the diagnostic query
# into a new cause of failure.
for mode in failed zero timeout; do
  out_invalid="$tmp/$mode"
  if FAKE_SCAN_MODE="$mode" run_bash "$fetch" --profile dev --region ap-southeast-1 --scan-config-arn "$config_arn" --output-dir "$out_invalid" --poll-interval 1 >/dev/null 2>&1; then
    echo "expected $mode scan to return non-zero" >&2
    exit 1
  fi
  test -s "$out_invalid/scan.json"
  python3 - "$out_invalid/target-status.json" <<'PY'
import json, sys
targets = json.load(open(sys.argv[1]))["targets"]
assert len(targets) == 2
assert targets[0]["targetStatusReason"] == "SCAN_IN_PROGRESS"
assert targets[1]["targetStatusReason"] == "SSM_UNMANAGED"
PY
done

for diagnostic_mode in unavailable invalid; do
  out_diagnostic="$tmp/$diagnostic_mode"
  if FAKE_SCAN_MODE=failed FAKE_TARGET_AGG_MODE="$diagnostic_mode" run_bash "$fetch" --profile dev --region ap-southeast-1 --scan-config-arn "$config_arn" --output-dir "$out_diagnostic" --poll-interval 1 >/dev/null 2>&1; then
    echo "expected failed scan with $diagnostic_mode diagnostic to return non-zero" >&2
    exit 1
  fi
  test -s "$out_diagnostic/scan.json"
  if [[ "$diagnostic_mode" == unavailable ]]; then
    expected_error=TARGET_AGGREGATION_UNAVAILABLE
  else
    expected_error=TARGET_AGGREGATION_INVALID_RESPONSE
  fi
  python3 - "$out_diagnostic/target-status.json" "$expected_error" <<'PY'
import json, sys
status = json.load(open(sys.argv[1]))
assert status["targets"] == []
assert status["diagnosticError"] == sys.argv[2]
PY
done
run_bash "$create" --profile dev --region ap-southeast-1 --instance-id i-0123456789abcdef0 --scan-name scan-123 --output-dir "$out_create" >/dev/null
python3 -m json.tool "$out_create/scan-config.json" >/dev/null
python3 - "$FAKE_TARGETS" <<'PY'
import json, sys
payload = json.loads(open(sys.argv[1]).readline())
assert payload["accountIds"] == ["SELF"]
assert payload["targetResourceTags"]["instance_id"] == ["i-0123456789abcdef0"]
PY

out_recover="$tmp/recover space ' quote"
run_bash "$create" --profile dev --region ap-southeast-1 --scan-config-arn "$org_config_arn" --output-dir "$out_recover" >/dev/null
test "$(cat "$out_recover/scan-config-arn.txt")" = "$org_config_arn"

before="$(wc -l < "$FAKE_AWS_CALLS")"
if run_bash "$fetch" --profile dev --region ap-southeast-1 --scan-config-arn "${config_arn};bad" --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
if run_bash "$fetch" --profile dev --region ap-southeast-1 --scan-config-arn 'arn:aws:inspector2:ap-southeast-1:123456789012:cis-scan-configuration/config-123' --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
if run_bash "$create" --profile dev --region ap-southeast-1 --instance-id 'i-0123456789abcdef0;bad' --scan-name scan-123 --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
if run_bash "$create" --profile dev --region ap-southeast-1 --instance-id i-0123456789abcdef0 --scan-name 'scan;bad' --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
if run_bash "$pipeline" --profile 'dev;bad' --region ap-southeast-1 --instance-id i-0123456789abcdef0 --scan-name scan-123 --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
test "$before" = "$(wc -l < "$FAKE_AWS_CALLS")"

printf 'fake_aws_interception=PASS calls=%s\n' "$(wc -l < "$FAKE_AWS_CALLS")"
echo "cis command-construction tests passed"
