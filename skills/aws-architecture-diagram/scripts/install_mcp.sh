#!/usr/bin/env bash
set -euo pipefail

version="${DRAWIO_MCP_VERSION:-1.4.0}"
config="${CODEX_HOME:-$HOME/.codex}/config.toml"
stamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="$HOME/back/codex/drawio-mcp-$stamp"

command -v codex >/dev/null 2>&1 || { printf 'FAIL codex not found\n' >&2; exit 3; }
command -v node >/dev/null 2>&1 || { printf 'FAIL node not found\n' >&2; exit 3; }
command -v npx >/dev/null 2>&1 || { printf 'FAIL npx not found\n' >&2; exit 3; }

if codex mcp get drawio >/dev/null 2>&1; then
  current="$(codex mcp get drawio)"
  if grep -Fq "@drawio/mcp@$version" <<<"$current"; then
    printf 'PASS drawio MCP already configured at %s\n' "$version"
    exit 0
  fi
  printf 'FAIL drawio MCP already exists with different configuration; review it before replacement\n' >&2
  exit 4
fi

mkdir -p "$backup_dir"
if [[ -f "$config" ]]; then
  cp -a "$config" "$backup_dir/config.toml"
fi
codex mcp add drawio -- npx -y "@drawio/mcp@$version"
codex mcp get drawio
printf 'PASS backup=%s version=%s\n' "$backup_dir" "$version"
