#!/usr/bin/env bash
set -euo pipefail

venv="${AWS_ARCH_DIAGRAM_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/aws-architecture-diagram-venv}"
if [[ ! -x "$venv/bin/python" ]]; then
  printf 'FAIL Python environment missing; run scripts/bootstrap_python.sh\n' >&2
  exit 3
fi
exec "$venv/bin/python" "$@"
