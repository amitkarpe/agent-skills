#!/usr/bin/env bash
set -euo pipefail

ROOT=${AGENT_WEB_ROOT:-/opt/agent-web}
URL_BASE=${AGENT_WEB_URL:-http://192.168.0.9}
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="${SKILL_DIR}/templates"
EVIDENCE_ROOT=${AGENT_WEB_EVIDENCE_ROOT:-/home/dev/.AGENTS-temp/agent-web-reporting}

usage() {
  cat >&2 <<'EOF'
usage:
  publish-html-report.sh --source <file.html> --lane <lane> (--slug <name>|--index) [--archive] [--update-index] [--no-validate]
  publish-html-report.sh --new --lane <lane> --slug <name> --title <title> [--summary <text>] [--output-dir <dir>]

Publishes a sanitized static HTML report into /opt/agent-web/<lane>/ and prints
the resulting LAN URL. The --new mode creates a Genesis starter report source
file and prints the created path; it does not publish by itself.
EOF
}

html_escape() {
  local value=$1
  value=${value//&/&amp;}
  value=${value//</&lt;}
  value=${value//>/&gt;}
  value=${value//\"/&quot;}
  printf '%s' "$value"
}

validate_lane_slug() {
  if [[ ! "$LANE" =~ ^[a-z0-9][a-z0-9._-]*$ ]]; then
    echo "invalid lane: $LANE" >&2
    exit 2
  fi

  if [[ -n "$SLUG" && ! "$SLUG" =~ ^[a-z0-9][a-z0-9._-]*$ ]]; then
    echo "invalid slug: $SLUG" >&2
    exit 2
  fi

  if [[ -n "$SLUG" && "$SLUG" == *.html ]]; then
    echo "slug must not include .html: $SLUG" >&2
    exit 2
  fi
}

validate_html_source() {
  local source=$1

  if [[ ! -f "$source" ]]; then
    echo "source not found: $source" >&2
    exit 1
  fi

  if ! grep -Eiq '<!doctype html|<html[ >]' "$source"; then
    echo "source does not look like HTML: $source" >&2
    exit 1
  fi

  if grep -Eiq '(AWS_SECRET_ACCESS_KEY|BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|PRIVATE KEY|seed phrase|wallet|api[_-]?token|password=|passwd=)' "$source"; then
    echo "source failed basic secret-pattern check: $source" >&2
    exit 1
  fi

  if ! grep -Eiq '<title>[^<]+</title>' "$source"; then
    echo "warning: source missing <title>: $source" >&2
  fi

  if ! grep -Eiq '<h1([^>]*)>[^<]+' "$source"; then
    echo "warning: source missing <h1>: $source" >&2
  fi

  if ! grep -Eiq 'updated|timestamp|generated' "$source"; then
    echo "warning: source missing updated/timestamp marker: $source" >&2
  fi
}

render_template() {
  local template=$1
  local output=$2
  local title=$3
  local summary=$4
  local updated=$5
  local status=${6:-Ready}
  local risk=${7:-Low}
  local next=${8:-Review}
  local current_status=${9:-Put the most important status or decision here.}
  local url="${URL_BASE%/}/${LANE}/${SLUG}.html"

  local title_esc summary_esc updated_esc status_esc risk_esc next_esc current_esc url_esc lane_esc
  title_esc=$(html_escape "$title")
  summary_esc=$(html_escape "$summary")
  updated_esc=$(html_escape "$updated")
  status_esc=$(html_escape "$status")
  risk_esc=$(html_escape "$risk")
  next_esc=$(html_escape "$next")
  current_esc=$(html_escape "$current_status")
  url_esc=$(html_escape "$url")
  lane_esc=$(html_escape "$LANE")

  python3 - "$template" "$output" \
    "$title_esc" "$summary_esc" "$lane_esc" "$updated_esc" \
    "$status_esc" "$risk_esc" "$next_esc" "$current_esc" "$url_esc" <<'PY'
from pathlib import Path
import sys

template, output, title, summary, lane, updated, status, risk, next_action, current_status, url = sys.argv[1:]
text = Path(template).read_text(encoding="utf-8")
replacements = {
    "{{TITLE}}": title,
    "{{SUMMARY}}": summary,
    "{{LANE}}": lane,
    "{{UPDATED}}": updated,
    "{{STATUS}}": status,
    "{{RISK}}": risk,
    "{{NEXT}}": next_action,
    "{{CURRENT_STATUS}}": current_status,
    "{{URL}}": url,
}
for key, value in replacements.items():
    text = text.replace(key, value)
Path(output).write_text(text, encoding="utf-8")
PY
}

generate_lane_index() {
  local target_dir=$1
  local archive_dir=$2
  local lane=$3
  local updated=$4
  local index_source
  index_source="${archive_dir}/index-source-$(date -u '+%Y%m%dT%H%M%SZ').html"
  local index_target="${target_dir}/index.html"
  local title="${lane} reports"
  local summary="Latest static HTML reports for lane ${lane}."
  local rows_file
  rows_file=$(mktemp)

  find "$target_dir" -maxdepth 1 -type f -name '*.html' ! -name 'index.html' -printf '%T@ %f\n' \
    | sort -rn \
    | head -20 \
    | while read -r _mtime file_name; do
        local file_esc updated_label
        file_esc=$(html_escape "$file_name")
        updated_label=$(date -r "${target_dir}/${file_name}" '+%Y-%m-%d %H:%M %Z')
        printf '          <tr><td><a href="%s">%s</a></td><td>%s</td></tr>\n' "$file_esc" "$file_esc" "$updated_label"
      done > "$rows_file"

  if [[ ! -s "$rows_file" ]]; then
    printf '          <tr><td colspan="2">No reports found.</td></tr>\n' > "$rows_file"
  fi

  python3 - "$TEMPLATE_DIR/genesis-dashboard.html" "$index_source" \
    "$(html_escape "$title")" "$(html_escape "$summary")" "$(html_escape "$lane")" "$(html_escape "$updated")" "$rows_file" <<'PY'
from pathlib import Path
import sys

template, output, title, summary, lane, updated, rows_file = sys.argv[1:]
text = Path(template).read_text(encoding="utf-8")
rows = Path(rows_file).read_text(encoding="utf-8").rstrip()
for key, value in {
    "{{TITLE}}": title,
    "{{SUMMARY}}": summary,
    "{{LANE}}": lane,
    "{{UPDATED}}": updated,
    "{{REPORT_ROWS}}": rows,
}.items():
    text = text.replace(key, value)
Path(output).write_text(text, encoding="utf-8")
PY
  rm -f "$rows_file"
  validate_html_source "$index_source"

  local index_sudo_cmd=()
  if [[ ${EUID} -ne 0 && ( ! -w "$target_dir" || ( -e "$index_target" && ! -O "$index_target" ) ) ]]; then
    index_sudo_cmd=(sudo)
  fi

  if [[ -f "$index_target" ]]; then
    local backup_name
    backup_name="index-$(date -u '+%Y%m%dT%H%M%SZ').html"
    "${index_sudo_cmd[@]}" cp -p "$index_target" "${archive_dir}/${backup_name}"
  fi

  "${index_sudo_cmd[@]}" cp "$index_source" "$index_target"
  "${index_sudo_cmd[@]}" chmod 0644 "$index_target"

  printf 'index: %s\n' "$index_target"
  printf 'index_url: %s/%s/\n' "${URL_BASE%/}" "$lane"
}

SOURCE=""
LANE=""
SLUG=""
INDEX=0
ARCHIVE=0
VALIDATE=1
NEW=0
TITLE=""
SUMMARY="Starter Genesis report."
OUTPUT_DIR=""
UPDATE_INDEX=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --new)
      NEW=1
      shift
      ;;
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
    --update-index)
      UPDATE_INDEX=1
      shift
      ;;
    --no-validate)
      VALIDATE=0
      shift
      ;;
    --title)
      TITLE=${2:-}
      shift 2
      ;;
    --summary)
      SUMMARY=${2:-}
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR=${2:-}
      shift 2
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

if [[ -z "$LANE" ]]; then
  usage
  exit 2
fi

validate_lane_slug

if [[ "$NEW" -eq 1 ]]; then
  if [[ -z "$SLUG" || -z "$TITLE" ]]; then
    echo "--new requires --lane, --slug, and --title" >&2
    usage
    exit 2
  fi

  if [[ "$INDEX" -eq 1 ]]; then
    echo "--new does not support --index" >&2
    exit 2
  fi

  if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="${EVIDENCE_ROOT}/${LANE}"
  fi

  mkdir -p "$OUTPUT_DIR"
  SOURCE="${OUTPUT_DIR}/${SLUG}.html"
  render_template "$TEMPLATE_DIR/genesis-report.html" "$SOURCE" "$TITLE" "$SUMMARY" "$(date '+%Y-%m-%d %H:%M %Z')"
  if [[ "$VALIDATE" -eq 1 ]]; then
    validate_html_source "$SOURCE"
  fi
  printf 'created: %s\n' "$SOURCE"
  exit 0
fi

if [[ -z "$SOURCE" ]]; then
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

if [[ "$VALIDATE" -eq 1 ]]; then
  validate_html_source "$SOURCE"
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

if [[ "$VALIDATE" -eq 1 ]] && command -v curl >/dev/null 2>&1; then
  if curl -fsSI --max-time 5 "$url" >/dev/null; then
    printf 'validated: %s\n' "$url"
  else
    echo "warning: published but URL validation failed: $url" >&2
  fi
fi

if [[ "$UPDATE_INDEX" -eq 1 ]]; then
  generate_lane_index "$target_dir" "$archive_dir" "$LANE" "$(date '+%Y-%m-%d %H:%M %Z')"
fi
