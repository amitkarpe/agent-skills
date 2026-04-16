#!/usr/bin/env bash
# inspector_cis_reduce_failed_controls.sh
# Read aggregated-checks.json from --output-dir and reduce to checks
# where statusCounts.failed > 0. Saves failed-controls.json.
set -euo pipefail

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found (required for JSON parsing)"; exit 1; }

usage() {
  echo "Usage: $0 --output-dir <dir>"
  exit 1
}

OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$OUTPUT_DIR" ]] && usage

INPUT="$OUTPUT_DIR/aggregated-checks.json"
OUTPUT="$OUTPUT_DIR/failed-controls.json"

[[ ! -f "$INPUT" ]] && { echo "[reduce] ERROR: $INPUT not found"; exit 1; }

log() { echo "[reduce] $*"; }

python3 - "$INPUT" "$OUTPUT" <<'EOF'
import sys, json

with open(sys.argv[1]) as f:
    data = json.load(f)

# handle both raw list and wrapped {"checkAggregations": [...]}
checks = data.get("checkAggregations", data) if isinstance(data, dict) else data

failed = [
    c for c in checks
    if c.get("statusCounts", {}).get("failed", 0) > 0
]

with open(sys.argv[2], "w") as f:
    json.dump(failed, f, indent=2)

print(f"Total checks: {len(checks)}")
print(f"Failed checks: {len(failed)}")
EOF

log "Reduced failed controls saved to $OUTPUT"
