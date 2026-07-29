#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"

cat > "$tmp/bin/aws" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%q ' "$@" >> "$FAKE_AWS_CALLS"
printf '\n' >> "$FAKE_AWS_CALLS"
for ((i=1; i <= $#; i++)); do
  if [[ "${!i}" == "--parameters" ]]; then
    j=$((i + 1))
    printf '%s' "${!j}" | python3 -m json.tool >/dev/null
    printf '%s\n' "${!j}" >> "$FAKE_PARAMETERS"
  fi
done
case " $* " in
  *" ssm send-command "*) echo "cmd-${RANDOM}" ;;
  *" get-command-invocation "*)
    if [[ " $* " == *" Status "* ]]; then echo "Success"; else echo "fake output"; fi
    ;;
  *) echo "unexpected fake aws arguments: $*" >&2; exit 1 ;;
esac
EOF
chmod +x "$tmp/bin/aws"

export PATH="$tmp/bin:$PATH"
run_bash() { env -u BASH_ENV PATH="$PATH" /bin/bash "$@"; }
expected_aws="$tmp/bin/aws"
assert_fake_aws() { run_bash -c 'test "$(command -v aws)" = "$1"' bash "$expected_aws"; }
assert_fake_aws
export FAKE_AWS_CALLS="$tmp/calls.log"
export FAKE_PARAMETERS="$tmp/parameters.jsonl"
: > "$FAKE_AWS_CALLS"
: > "$FAKE_PARAMETERS"

trace="$repo/skills/gitlab-triage/scripts/trace-gitlab-backend.sh"
dns="$repo/skills/gitlab-triage/scripts/check-cloudos-gitlab-dns.sh"
valid_id_a="i-0123456789abcdef0"
valid_id_b="i-0abcdef1234567890"

run_bash "$trace" dev ap-southeast-1 "$valid_id_a" "$valid_id_b" gitlab.example.com >/dev/null
run_bash "$dns" dev ap-southeast-1 gitlab.example.com "$valid_id_a" >/dev/null
test -s "$FAKE_AWS_CALLS"
python3 - "$FAKE_PARAMETERS" <<'PY'
import json, sys
for line in open(sys.argv[1]):
    command = json.loads(line)["commands"][0]
    assert "gitlab.example.com" not in command
    assert "base64 -d" in command
PY

before="$(wc -l < "$FAKE_AWS_CALLS")"
hostile=(
  'bad host.example'
  'bad"quote.example'
  'bad;semi.example'
  'bad$(id).example'
  "bad$(printf '\\140')id$(printf '\\140').example"
  'bad/path.example'
  'bad.example?x=1'
)
for fqdn in "${hostile[@]}"; do
  if run_bash "$trace" dev ap-southeast-1 "$valid_id_a" "$valid_id_b" "$fqdn" >/dev/null 2>&1; then
    echo "hostile FQDN accepted: $fqdn" >&2
    exit 1
  fi
done
if run_bash "$dns" dev 'bad;region' gitlab.example.com "$valid_id_a" >/dev/null 2>&1; then exit 1; fi
if run_bash "$dns" dev ap-southeast-1 gitlab.example.com 'i-bad' >/dev/null 2>&1; then exit 1; fi
if run_bash "$trace" 'bad;profile' ap-southeast-1 "$valid_id_a" "$valid_id_b" >/dev/null 2>&1; then exit 1; fi
test "$before" = "$(wc -l < "$FAKE_AWS_CALLS")"

printf 'fake_aws_interception=PASS calls=%s\n' "$(wc -l < "$FAKE_AWS_CALLS")"
echo "gitlab command-construction tests passed"
