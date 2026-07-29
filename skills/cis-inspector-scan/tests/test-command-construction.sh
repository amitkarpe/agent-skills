#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"
config_arn="arn:aws:inspector2:ap-southeast-1:123456789012:cis-scan-configuration/config-123"
scan_arn="arn:aws:inspector2:ap-southeast-1:123456789012:cis-scan/scan-123"
export FAKE_AWS_CALLS="$tmp/calls.log"
export FAKE_TARGETS="$tmp/targets.jsonl"
export FAKE_CONFIG_ARN="$config_arn"
export FAKE_SCAN_ARN="$scan_arn"
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
  *" inspector2 list-cis-scans "*) printf '{"scans":[{"scanConfigurationArn":"%s","scanArn":"%s","status":"COMPLETED","totalChecks":1}]}\n' "$FAKE_CONFIG_ARN" "$FAKE_SCAN_ARN" ;;
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
run_bash "$create" --profile dev --region ap-southeast-1 --instance-id i-0123456789abcdef0 --scan-name scan-123 --output-dir "$out_create" >/dev/null
python3 -m json.tool "$out_create/scan-config.json" >/dev/null
python3 - "$FAKE_TARGETS" <<'PY'
import json, sys
payload = json.loads(open(sys.argv[1]).readline())
assert payload["accountIds"] == ["SELF"]
assert payload["targetResourceTags"]["instance_id"] == ["i-0123456789abcdef0"]
PY

before="$(wc -l < "$FAKE_AWS_CALLS")"
if run_bash "$fetch" --profile dev --region ap-southeast-1 --scan-config-arn "${config_arn};bad" --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
if run_bash "$create" --profile dev --region ap-southeast-1 --instance-id 'i-0123456789abcdef0;bad' --scan-name scan-123 --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
if run_bash "$create" --profile dev --region ap-southeast-1 --instance-id i-0123456789abcdef0 --scan-name 'scan;bad' --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
if run_bash "$pipeline" --profile 'dev;bad' --region ap-southeast-1 --instance-id i-0123456789abcdef0 --scan-name scan-123 --output-dir "$tmp/no-call" >/dev/null 2>&1; then exit 1; fi
test "$before" = "$(wc -l < "$FAKE_AWS_CALLS")"

printf 'fake_aws_interception=PASS calls=%s\n' "$(wc -l < "$FAKE_AWS_CALLS")"
echo "cis command-construction tests passed"
