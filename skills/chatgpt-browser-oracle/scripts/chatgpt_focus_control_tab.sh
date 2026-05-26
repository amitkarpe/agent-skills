#!/usr/bin/env bash
set -euo pipefail

host="${CHATGPT_CDP_HOST:-127.0.0.1}"
port="${CHATGPT_CDP_PORT:-9222}"
service="${CHATGPT_CHROME_SERVICE:-oracle-chrome-amit.service}"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

if command -v systemctl >/dev/null 2>&1; then
  if ! systemctl --user is-active --quiet "$service"; then
    echo "chrome_service=inactive service=$service"
    exit 2
  fi
fi

curl -fsS "http://$host:$port/json/version" >/dev/null

window_id=""
if command -v wmctrl >/dev/null 2>&1; then
  window_id="$(wmctrl -l | awk 'BEGIN{IGNORECASE=1} /chatgpt.*chrome|chrome.*chatgpt/ {print $1; exit}')"
  if [[ -z "$window_id" ]]; then
    window_id="$(wmctrl -l | awk 'BEGIN{IGNORECASE=1} /google chrome|chrome/ {print $1; exit}')"
  fi
fi

if [[ -n "$window_id" ]] && command -v xdotool >/dev/null 2>&1; then
  xdotool windowactivate "$window_id"
  sleep 0.4
  xdotool key ctrl+1
  echo "focused=true window_id=$window_id control_tab=1"
else
  echo "focused=false devtools=true reason=no_window_tool_or_window"
fi
