#!/usr/bin/env bash
set -euo pipefail

expected="${DRAWIO_MCP_VERSION:-1.4.0}"
for command_name in node npm npx codex; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'FAIL missing command: %s\n' "$command_name" >&2
    exit 3
  }
done

node_major="$(node --version | sed 's/^v//' | cut -d. -f1)"
(( node_major >= 18 )) || { printf 'FAIL Node.js 18 or newer required\n' >&2; exit 3; }

details="$(codex mcp get drawio 2>/dev/null || true)"
[[ -n "$details" ]] || { printf 'FAIL drawio MCP is not configured\n' >&2; exit 4; }
grep -Fq "@drawio/mcp@$expected" <<<"$details" || {
  printf 'FAIL expected @drawio/mcp@%s\n' "$expected" >&2
  exit 4
}

printf 'PASS node=%s npm=%s drawio-mcp=%s\n' "$(node --version)" "$(npm --version)" "$expected"
printf 'NOTE restart Codex after MCP configuration so tools are discovered\n'
