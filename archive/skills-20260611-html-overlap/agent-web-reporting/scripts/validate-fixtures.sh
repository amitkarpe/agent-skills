#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

export AGENT_WEB_ROOT="$TMP_DIR/web"
export AGENT_WEB_URL="http://127.0.0.1"
export AGENT_WEB_EVIDENCE_ROOT="$TMP_DIR/evidence"
export AGENT_WEB_VALIDATE_URL=0

assert_file() {
  local path=$1
  if [[ ! -f "$path" ]]; then
    echo "missing expected file: $path" >&2
    exit 1
  fi
}

assert_contains() {
  local path=$1
  local pattern=$2
  if ! grep -Fq "$pattern" "$path"; then
    echo "missing expected text in $path: $pattern" >&2
    exit 1
  fi
}

starter_output="$(
  "$ROOT_DIR/scripts/publish-html-report.sh" \
    --new \
    --lane fixture \
    --slug generated \
    --title "Generated Fixture" \
    --summary "Fixture starter report." \
    --status "Ready" \
    --risk "Low" \
    --next "Publish" \
    --current-status "Fixture current status rendered from CLI flags." \
    --output-dir "$TMP_DIR/sources"
)"
starter_source="$(printf '%s\n' "$starter_output" | awk -F': ' '/^created:/ {print $2}')"

assert_file "$starter_source"
assert_contains "$starter_source" "<title>Generated Fixture</title>"
assert_contains "$starter_source" "Fixture starter report."
assert_contains "$starter_source" "Fixture current status rendered from CLI flags."
assert_contains "$starter_source" "<strong>Publish</strong>"

publish_output="$(
  "$ROOT_DIR/scripts/publish-html-report.sh" \
    --source "$ROOT_DIR/fixtures/sample-source-report.html" \
    --lane fixture \
    --slug sample \
    --archive \
    --update-index
)"

assert_contains <(printf '%s\n' "$publish_output") "url: http://127.0.0.1/fixture/sample.html"

report_path="$AGENT_WEB_ROOT/fixture/sample.html"
index_path="$AGENT_WEB_ROOT/fixture/index.html"
assert_file "$report_path"
assert_file "$index_path"
assert_contains "$report_path" "<title>Sample Agent Report</title>"
assert_contains "$index_path" "sample.html"
assert_contains "$index_path" "Static index generated from published lane HTML files."

echo "OK: fixture generation and publishing passed"
