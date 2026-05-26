#!/usr/bin/env bash
set -euo pipefail

ROOT=${AGENT_WEB_ROOT:-/opt/agent-web}
URL_BASE=${AGENT_WEB_URL:-http://192.168.0.9}

usage() {
  cat >&2 <<'EOF'
usage: publish-html-report.sh --source <file.html> --lane <lane> (--slug <name>|--index) [--archive]

Publishes a sanitized static HTML report into /opt/agent-web/<lane>/ and prints
the resulting LAN URL.
EOF
}

SOURCE=""
LANE=""
SLUG=""
INDEX=0
ARCHIVE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE=${2:-}
      shift 2
      ;;
    --lane)
      LANE=${2:-}
      shift 2
      ;;
    --slug)
      SLUG=${2:-}
      shift 2
      ;;
    --index)
      INDEX=1
      shift
      ;;
    --archive)
      ARCHIVE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$SOURCE" || -z "$LANE" ]]; then
  usage
  exit 2
fi

if [[ "$INDEX" -eq 1 && -n "$SLUG" ]]; then
  echo "--index and --slug are mutually exclusive" >&2
  exit 2
fi

if [[ "$INDEX" -eq 0 && -z "$SLUG" ]]; then
  echo "provide --slug or --index" >&2
  exit 2
fi

if [[ ! -f "$SOURCE" ]]; then
  echo "source not found: $SOURCE" >&2
  exit 1
fi

if [[ ! "$LANE" =~ ^[a-z0-9][a-z0-9._-]*$ ]]; then
  echo "invalid lane: $LANE" >&2
  exit 2
fi

if [[ -n "$SLUG" && ! "$SLUG" =~ ^[a-z0-9][a-z0-9._-]*$ ]]; then
  echo "invalid slug: $SLUG" >&2
  exit 2
fi

if ! grep -Eiq '<!doctype html|<html[ >]' "$SOURCE"; then
  echo "source does not look like HTML: $SOURCE" >&2
  exit 1
fi

if grep -Eiq '(AWS_SECRET_ACCESS_KEY|BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|PRIVATE KEY|seed phrase|wallet|api[_-]?token|password=|passwd=)' "$SOURCE"; then
  echo "source failed basic secret-pattern check: $SOURCE" >&2
  exit 1
fi

target_dir="${ROOT}/${LANE}"
archive_dir="${target_dir}/archive"
target_name="index.html"
if [[ "$INDEX" -eq 0 ]]; then
  target_name="${SLUG}.html"
fi
target="${target_dir}/${target_name}"

sudo_cmd=()
if [[ ${EUID} -ne 0 && ! -w "$ROOT" ]]; then
  sudo_cmd=(sudo)
fi

"${sudo_cmd[@]}" mkdir -p "$target_dir" "$archive_dir"

if [[ -f "$target" ]]; then
  backup_name="${target_name%.html}-$(date -u '+%Y%m%dT%H%M%SZ').html"
  "${sudo_cmd[@]}" cp -p "$target" "${archive_dir}/${backup_name}"
fi

"${sudo_cmd[@]}" cp "$SOURCE" "$target"
"${sudo_cmd[@]}" chmod 0644 "$target"

if [[ "$ARCHIVE" -eq 1 && "$INDEX" -eq 0 ]]; then
  archive_name="${SLUG}-$(date -u '+%Y%m%dT%H%M%SZ').html"
  "${sudo_cmd[@]}" cp -p "$target" "${archive_dir}/${archive_name}"
fi

url="${URL_BASE%/}/${LANE}/${target_name}"
if [[ "$INDEX" -eq 1 ]]; then
  url="${URL_BASE%/}/${LANE}/"
fi

printf 'published: %s\n' "$target"
printf 'url: %s\n' "$url"
