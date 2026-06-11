#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "scan root: $ROOT_DIR"

forbidden_files="$(
  find "$ROOT_DIR" -type f \
    \( -name '.env' -o -name '.env-*' -o -name 'auth.json' \
       -o -name 'hosts.yml' -o -name '*.pem' -o -name '*.key' \) \
    -print
)"

if [[ -n "$forbidden_files" ]]; then
  printf '%s\n' "$forbidden_files"
  echo "FAIL: forbidden secret/auth files are present" >&2
  exit 1
fi

secret_value_hits="$(
  rg -n --hidden --glob '!.git/**' \
    '(^|[^A-Za-z0-9_])sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----|access_token"\s*:\s*"[^"]+|refresh_token"\s*:\s*"[^"]+|private_key\s*[:=]' \
    "$ROOT_DIR" || true
)"

if [[ -n "$secret_value_hits" ]]; then
  printf '%s\n' "$secret_value_hits"
  echo "FAIL: possible secret values found" >&2
  exit 1
fi

echo "OK: no forbidden files or obvious secret values"
