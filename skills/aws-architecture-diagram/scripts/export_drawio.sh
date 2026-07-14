#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'Usage: %s INPUT.drawio OUTPUT_DIR\n' "${0##*/}" >&2
  exit 2
fi

input="$(realpath "$1")"
output_dir="$(realpath -m "$2")"
mkdir -p "$output_dir"
base="$(basename "$input" .drawio)"
svg="$output_dir/$base.svg"
png="$output_dir/$base.png"

drawio_bin="${DRAWIO_BIN:-}"
if [[ -z "$drawio_bin" ]] && command -v draw.io.exe >/dev/null 2>&1; then
  drawio_bin="$(command -v draw.io.exe)"
elif [[ -z "$drawio_bin" ]] && command -v drawio >/dev/null 2>&1; then
  drawio_bin="$(command -v drawio)"
elif [[ -z "$drawio_bin" ]] && command -v draw.io >/dev/null 2>&1; then
  drawio_bin="$(command -v draw.io)"
fi
[[ -n "$drawio_bin" ]] || { printf 'FAIL draw.io Desktop CLI not found; set DRAWIO_BIN\n' >&2; exit 3; }

lock_file="${DRAWIO_EXPORT_LOCK_FILE:-${XDG_RUNTIME_DIR:-/tmp}/aws-architecture-diagram-drawio.lock}"
mkdir -p "$(dirname "$lock_file")"
exec 9>"$lock_file"
flock -w "${DRAWIO_LOCK_TIMEOUT_SECONDS:-120}" 9 || {
  printf 'FAIL timed out waiting for draw.io export lock: %s\n' "$lock_file" >&2
  exit 3
}

actual_version="$(DRAWIO_DISABLE_UPDATE=true timeout 20 "$drawio_bin" --version 2>&1 | tr -d '\r' | awk 'NF {line=$0} END {print line}')"
if [[ -n "${EXPECTED_DRAWIO_VERSION:-}" && "$actual_version" != "$EXPECTED_DRAWIO_VERSION" && "${ALLOW_DRAWIO_VERSION_MISMATCH:-NO}" != YES ]]; then
  printf 'FAIL draw.io version expected=%s actual=%s\n' "$EXPECTED_DRAWIO_VERSION" "$actual_version" >&2
  exit 3
fi

if [[ "$drawio_bin" == *.exe ]]; then
  input_arg="$(wslpath -w "$input")"
  svg_arg="$(wslpath -w "$svg")"
  png_arg="$(wslpath -w "$png")"
else
  input_arg="$input"
  svg_arg="$svg"
  png_arg="$png"
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
python_runner="$root/scripts/python.sh"
attempts="${DRAWIO_EXPORT_ATTEMPTS:-3}"
settle_seconds="${DRAWIO_EXPORT_SETTLE_SECONDS:-2}"
timeout_seconds="${DRAWIO_TIMEOUT_SECONDS:-90}"

validate_png() {
  "$python_runner" - "$png" "${DRAWIO_MAX_BLACK_RATIO:-0.05}" "${ALLOW_DARK_RENDER:-NO}" <<'PY'
import sys
from pathlib import Path
from PIL import Image

path = Path(sys.argv[1])
max_black_ratio = float(sys.argv[2])
allow_dark = sys.argv[3] == "YES"
data = path.read_bytes() if path.exists() else b""
if data[:8] != b"\x89PNG\r\n\x1a\n":
    raise SystemExit('FAIL invalid PNG signature')
image = Image.open(path).convert("RGB")
width, height = image.size
if width < 1000 or height < 600:
    raise SystemExit(f'FAIL PNG too small: {width}x{height}')
black = sum(1 for red, green, blue in image.get_flattened_data()
            if red < 12 and green < 12 and blue < 12)
black_ratio = black / (width * height)
if not allow_dark and black_ratio > max_black_ratio:
    raise SystemExit(
        f'FAIL suspicious black render: ratio={black_ratio:.3%} '
        f'max={max_black_ratio:.3%}'
    )
print(f'PASS png={path} dimensions={width}x{height} black={black_ratio:.3%}')
PY
}

export_ok=NO
for ((attempt = 1; attempt <= attempts; attempt++)); do
  rm -f "$svg" "$png"
  sleep "$settle_seconds"
  if ! DRAWIO_DISABLE_UPDATE=true timeout "$timeout_seconds" "$drawio_bin" \
      -x -f svg -e --embed-svg-images --svg-theme light -b 12 \
      -o "$svg_arg" "$input_arg"; then
    printf 'WARN draw.io SVG export failed attempt=%s/%s\n' "$attempt" "$attempts" >&2
    continue
  fi
  sleep "$settle_seconds"
  if ! DRAWIO_DISABLE_UPDATE=true timeout "$timeout_seconds" "$drawio_bin" \
      -x -f png -b 12 -s "${PNG_SCALE:-1.5}" -o "$png_arg" "$input_arg"; then
    printf 'WARN draw.io PNG export failed attempt=%s/%s\n' "$attempt" "$attempts" >&2
    continue
  fi
  if [[ -s "$svg" && -s "$png" ]] && validate_png; then
    export_ok=YES
    break
  fi
  printf 'WARN rejected draw.io export attempt=%s/%s\n' "$attempt" "$attempts" >&2
done

[[ "$export_ok" == YES ]] || { printf 'FAIL draw.io export did not produce a valid render\n' >&2; exit 4; }
printf 'PASS drawio=%s svg=%s png=%s\n' "$actual_version" "$svg" "$png"
