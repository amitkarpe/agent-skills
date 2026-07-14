#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
venv="${AWS_ARCH_DIAGRAM_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/aws-architecture-diagram-venv}"
python_bin="${PYTHON_BIN:-python3}"

if [[ ! -x "$venv/bin/python" ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python "$python_bin" "$venv"
  else
    "$python_bin" -m venv "$venv"
  fi
fi

if command -v uv >/dev/null 2>&1; then
  uv pip sync --python "$venv/bin/python" "$root/requirements.lock"
else
  "$venv/bin/python" -m pip install --disable-pip-version-check -r "$root/requirements.lock"
fi

"$venv/bin/python" -c 'import PIL, cairosvg; print("PASS Pillow=" + PIL.__version__ + " CairoSVG=" + cairosvg.__version__)'
printf 'PASS python=%s\n' "$venv/bin/python"
