#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
python="$root/scripts/python.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# 0. Prove v2.4 accessibility and non-mutating clearance behavior first.
"$python" "$root/scripts/test_v24.py"

# 1. Validate the polished native-AWS example and preview renderer.
"$python" "$root/scripts/validate_spec.py" "$root/assets/examples/aws-3-tier-demo.spec.json"
"$python" "$root/scripts/generate_drawio.py" \
  "$root/assets/examples/aws-3-tier-demo.spec.json" \
  "$tmp/native-example.drawio"
"$python" "$root/scripts/validate_drawio.py" "$tmp/native-example.drawio"
"$python" "$root/scripts/render_preview.py" \
  "$tmp/native-example.drawio" "$tmp/native-example.svg" "$tmp/native-example.png" --scale 0.5
[[ -s "$tmp/native-example.drawio" && -s "$tmp/native-example.svg" && -s "$tmp/native-example.png" ]]

# 1b. Exercise offline AWS4 discovery and defensive XML validation.
"$python" "$root/scripts/search_aws4_shapes.py" parameter store --limit 3 > "$tmp/shape-search.json"
"$python" - "$tmp/shape-search.json" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
first = result["results"][0]
if first["shape"] != "parameter_store" or first["kind"] != "direct":
    raise SystemExit(f"FAIL unexpected shape search result: {first}")
PY

"$python" - "$tmp/native-example.drawio" "$tmp/invalid-shape.drawio" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8")
source = source.replace("resIcon=mxgraph.aws4.users", "resIcon=mxgraph.aws4.not_a_real_shape", 1)
Path(sys.argv[2]).write_text(source, encoding="utf-8")
PY
if "$python" "$root/scripts/validate_drawio.py" "$tmp/invalid-shape.drawio" >/dev/null 2>&1; then
  printf 'FAIL invented AWS4 shape passed validation\n' >&2
  exit 1
fi

"$python" - "$tmp/deep.drawio" <<'PY'
import sys
from pathlib import Path

Path(sys.argv[1]).write_text("<mxfile>" + "<x>" * 101 + "</x>" * 101 + "</mxfile>", encoding="utf-8")
PY
if "$python" "$root/scripts/validate_drawio.py" "$tmp/deep.drawio" >/dev/null 2>&1; then
  printf 'FAIL excessively deep XML passed validation\n' >&2
  exit 1
fi

# 2. Guard native AWS4 mapping, the vendor image URI, and deduplicated legend behavior.
"$python" "$root/scripts/generate_drawio.py" \
  "$root/assets/examples/ami-factory.spec.json" \
  "$tmp/ami-factory.drawio"
"$python" "$root/scripts/validate_drawio.py" "$tmp/ami-factory.drawio"
if grep -Fq ';base64,' "$tmp/ami-factory.drawio"; then
  printf 'FAIL semicolon-bearing data URI found\n' >&2
  exit 1
fi
"$python" - "$tmp/ami-factory.drawio" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
icons = [cell for cell in root.iter("mxCell") if cell.get("data-kind") == "resource-icon"]
native = [cell for cell in icons if cell.get("data-icon-source") == "drawio-native-aws4"]
vendor = [cell for cell in icons if cell.get("data-icon-source") == "vendor-local"]
if len(native) != 11 or len(vendor) != 1:
    raise SystemExit(
        f"FAIL expected 11 native AWS icons and one vendor icon, "
        f"found native={len(native)} vendor={len(vendor)}"
    )
PY
grep -Fq 'shape=mxgraph.aws4.parameter_store' "$tmp/ami-factory.drawio" || {
  printf 'FAIL direct Parameter Store shape is missing\n' >&2
  exit 1
}
legend_count="$(grep -o 'data-kind="legend-label"' "$tmp/ami-factory.drawio" | wc -l)"
if (( legend_count != 4 )); then
  printf 'FAIL expected 4 deduplicated legend labels, found %s\n' "$legend_count" >&2
  exit 1
fi

if [[ -n "${DRAWIO_BIN:-}" ]] || command -v draw.io.exe >/dev/null 2>&1 || \
  command -v drawio >/dev/null 2>&1 || command -v draw.io >/dev/null 2>&1; then
  "$root/scripts/export_drawio.sh" "$tmp/ami-factory.drawio" "$tmp"
  embedded_count="$(grep -o '<image ' "$tmp/ami-factory.svg" | wc -l)"
  if (( embedded_count != 1 )); then
    printf 'FAIL exact SVG expected one embedded vendor image, found %s\n' "$embedded_count" >&2
    exit 1
  fi
fi

# 3. Exercise the official icon catalogue path using an explicit local test fixture.
mkdir -p "$tmp/package/Architecture-Service-Icons"
cp "$root/assets/fallback-icons/aws-ec2.png" \
  "$tmp/package/Architecture-Service-Icons/Arch_Amazon-EC2_64.png"
(
  cd "$tmp/package"
  zip -q -r "$tmp/Icon-package_test.zip" .
)
"$python" "$root/scripts/prepare_aws_icons.py" \
  --package-zip "$tmp/Icon-package_test.zip" \
  --official-local-package \
  --output "$tmp/official-icons"

cat > "$tmp/minimal.json" <<'JSON'
{
  "id": "official-icon-review-test",
  "name": "Official Icon Review Test",
  "title": "Official AWS Icon Review Pipeline",
  "subtitle": "Two-pass deterministic skill self-test",
  "alt_text": "One Amazon EC2 service card proving official icon provenance and the two-pass accessible review pipeline.",
  "architecture_type": "overview",
  "audience": "Skill maintainers",
  "source_evidence": ["Generated self-test fixture"],
  "page": {"width": 1200, "height": 700, "background": "#FFFFFF"},
  "icon_mode": "official",
  "edge_color_mode": "source",
  "nodes": [
    {
      "id": "ec2",
      "provider": "aws",
      "label": "Amazon EC2\nTest instance",
      "icon_key": "amazon-ec2",
      "variant": "icon-left",
      "geometry": [390, 250, 420, 140],
      "fill": "#FFFFFF",
      "stroke": "#E8790C",
      "accent": "#E8790C",
      "icon_size": 72,
      "font_size": 18
    }
  ],
  "edges": [],
  "legend": false,
  "footer": {"status": "Self-test", "note": "Official icon fixture"}
}
JSON

review_dir="$tmp/review"
"$python" "$root/scripts/build_and_review.py" \
  "$tmp/minimal.json" "$review_dir" \
  --name official-test --pass-number 1 --renderer preview \
  --official-icons "$tmp/official-icons" --require-official-aws-icons --preview-scale 0.5
"$python" "$root/scripts/build_and_review.py" \
  "$tmp/minimal.json" "$review_dir" \
  --name official-test --pass-number 2 --renderer preview \
  --changes "Confirmed icon provenance, label transparency, spacing, and export dimensions." \
  --official-icons "$tmp/official-icons" --require-official-aws-icons --preview-scale 0.5
"$python" "$root/scripts/finalize_diagram.py" \
  "$review_dir" --name official-test --accept-preview --allow-warnings
"$python" "$root/scripts/validate_drawio.py" \
  "$review_dir/official-test.drawio" --require-official-aws-icons
[[ -s "$review_dir/official-test.drawio" && -s "$review_dir/official-test.review-summary.md" ]]

printf 'PASS self-test\n'
