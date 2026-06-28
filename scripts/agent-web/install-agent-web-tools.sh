#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${AGENT_WEB_BIN_DIR:-/opt/agent-web/bin}"
USER_BIN="${AGENT_WEB_USER_BIN:-$HOME/.local/bin}"

install_one() {
  local name="$1"
  install -m 0755 "$SCRIPT_DIR/$name" "$RUNTIME_DIR/$name"
  mkdir -p "$USER_BIN"
  install -m 0755 "$SCRIPT_DIR/$name" "$USER_BIN/$name"
}

mkdir -p "$RUNTIME_DIR"

install_one agent-report
install_one agent-web-www
install_one agent-report-smoke

if getent group agents >/dev/null 2>&1; then
  chgrp -R agents "$RUNTIME_DIR" /opt/agent-web/www 2>/dev/null || true
  chmod -R g+rwX "$RUNTIME_DIR" /opt/agent-web/www 2>/dev/null || true
  find "$RUNTIME_DIR" /opt/agent-web/www -type d -exec chmod g+s {} + 2>/dev/null || true
fi

if command -v setfacl >/dev/null 2>&1; then
  setfacl -R -m u:dev:rwx,u:hermes:rwx,g:agents:rwx "$RUNTIME_DIR" /opt/agent-web/www 2>/dev/null || true
  setfacl -R -d -m u:dev:rwx,u:hermes:rwx,g:agents:rwx "$RUNTIME_DIR" /opt/agent-web/www 2>/dev/null || true
fi

"$RUNTIME_DIR/agent-web-www" init
"$RUNTIME_DIR/agent-web-www" validate

printf 'installed agent-web tools\n'
printf 'runtime=%s\n' "$RUNTIME_DIR"
printf 'user_bin=%s\n' "$USER_BIN"
