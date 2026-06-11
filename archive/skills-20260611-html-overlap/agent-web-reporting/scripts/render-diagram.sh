#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  render-diagram.sh --type graphviz --source flow.dot --output flow.svg
  render-diagram.sh --type mermaid --source flow.mmd --output flow.svg

Renders local diagram source to SVG for embedding in static agent-web reports.
USAGE
}

type=""
source=""
output=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)
      type="${2:-}"
      shift 2
      ;;
    --source)
      source="${2:-}"
      shift 2
      ;;
    --output)
      output="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$type" || -z "$source" || -z "$output" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -r "$source" ]]; then
  echo "source is not readable: $source" >&2
  exit 1
fi

mkdir -p "$(dirname "$output")"

case "$type" in
  graphviz|dot)
    command -v dot >/dev/null || {
      echo "dot is not installed" >&2
      exit 1
    }
    dot -Tsvg "$source" > "$output"
    ;;
  mermaid|mmd)
    command -v mmdc >/dev/null || {
      echo "mmdc is not installed; install @mermaid-js/mermaid-cli" >&2
      exit 1
    }
    tmpdir="${TMPDIR:-/tmp}/agent-web-reporting-mermaid"
    mkdir -p "$tmpdir"
    chrome_path="${PUPPETEER_EXECUTABLE_PATH:-}"
    if [[ -z "$chrome_path" ]]; then
      chrome_path="$(
        find "$HOME/.cache/puppeteer/chrome" -type f -path '*/chrome-linux64/chrome' 2>/dev/null |
          sort -V |
          tail -n 1 || true
      )"
    fi
    if [[ -z "$chrome_path" || ! -x "$chrome_path" ]]; then
      echo "Puppeteer Chrome not found; run: browsers install chrome --path ~/.cache/puppeteer" >&2
      exit 1
    fi
    config="$tmpdir/puppeteer-config.json"
    printf '{"executablePath":"%s","args":["--no-sandbox","--disable-dev-shm-usage"]}\n' "$chrome_path" > "$config"
    mmdc -p "$config" -i "$source" -o "$output"
    ;;
  *)
    echo "unsupported diagram type: $type" >&2
    usage >&2
    exit 2
    ;;
esac

test -s "$output" || {
  echo "diagram output is empty: $output" >&2
  exit 1
}

echo "rendered: $output"
