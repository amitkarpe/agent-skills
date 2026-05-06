#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  stage-and-verify.sh --src /path/file --s3-uri s3://bucket/key --output-dir /path
                      [--profile p] [--region r]
EOF
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing dependency: $1" >&2
    exit 1
  }
}

need aws
need python3
need jq

SRC=""
S3_URI=""
OUTPUT_DIR=""
PROFILE=""
REGION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src) SRC="$2"; shift 2 ;;
    --s3-uri) S3_URI="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$SRC" || -z "$S3_URI" || -z "$OUTPUT_DIR" ]] && usage
[[ -f "$SRC" ]] || { echo "source file not found: $SRC" >&2; exit 1; }

mkdir -p "$OUTPUT_DIR"
LOG="$OUTPUT_DIR/run.log"
exec > >(tee -a "$LOG") 2> >(tee -a "$OUTPUT_DIR/run-errors.log" >&2)

AWS=(aws)
[[ -n "$PROFILE" ]] && AWS+=(--profile "$PROFILE")
[[ -n "$REGION" ]] && AWS+=(--region "$REGION")

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }

python3 - "$S3_URI" <<'PY' > "$OUTPUT_DIR/s3-location.txt"
import sys
uri = sys.argv[1]
if not uri.startswith("s3://"):
    raise SystemExit("s3 uri must start with s3://")
path = uri[5:]
bucket, _, key = path.partition("/")
print(bucket)
print(key)
PY

BUCKET=$(sed -n '1p' "$OUTPUT_DIR/s3-location.txt")
KEY=$(sed -n '2p' "$OUTPUT_DIR/s3-location.txt")

cp "$SRC" "$OUTPUT_DIR/$(basename "$SRC")"
printf '%s\n' "$S3_URI" > "$OUTPUT_DIR/s3-uri.txt"
log "uploading $SRC to $S3_URI"
"${AWS[@]}" s3 cp "$SRC" "$S3_URI"

log "listing uploaded object"
"${AWS[@]}" s3 ls "$S3_URI" > "$OUTPUT_DIR/s3-ls.txt"

log "reading head-object metadata"
"${AWS[@]}" s3api head-object --bucket "$BUCKET" --key "$KEY" > "$OUTPUT_DIR/head-object.json"

python3 - "$OUTPUT_DIR/head-object.json" "$S3_URI" <<'PY' | tee "$OUTPUT_DIR/summary.txt"
import json, sys
path, uri = sys.argv[1:]
with open(path) as f:
    data = json.load(f)
print(f"S3_URI\t{uri}")
print(f"SIZE\t{data.get('ContentLength')}")
print(f"LAST_MODIFIED\t{data.get('LastModified')}")
print(f"ETAG\t{data.get('ETag')}")
print(f"READY\tupload verified via head-object")
PY

cat > "$OUTPUT_DIR/fetch-example.sh" <<EOF
#!/usr/bin/env bash
aws ${PROFILE:+--profile $PROFILE }${REGION:+--region $REGION }s3 cp "$S3_URI" ./
EOF

log "saved evidence to $OUTPUT_DIR"
