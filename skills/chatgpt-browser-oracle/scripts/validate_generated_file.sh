#!/usr/bin/env bash
set -euo pipefail

file=""
expect=""
expect_name=""
min_bytes="1"
declare -a require_entries=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)
      file="$2"
      shift 2
      ;;
    --expect)
      expect="$2"
      shift 2
      ;;
    --expect-name)
      expect_name="$2"
      shift 2
      ;;
    --min-bytes)
      min_bytes="$2"
      shift 2
      ;;
    --require-entry)
      require_entries+=("$2")
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$file" || -z "$expect" ]]; then
  echo "usage: $0 --file <path> --expect <zip|docx|pptx|xlsx|pdf|html|js|image|gif>" >&2
  exit 2
fi

if [[ ! -s "$file" ]]; then
  echo "valid=false reason=missing_or_empty file=$file"
  exit 3
fi

if [[ -n "$expect_name" && "$(basename "$file")" != "$expect_name" ]]; then
  echo "valid=false reason=name_mismatch file=$file expect_name=$expect_name actual_name=$(basename "$file")"
  exit 4
fi

size="$(stat -c '%s' "$file")"
if ! [[ "$min_bytes" =~ ^[0-9]+$ ]]; then
  echo "valid=false reason=bad_min_bytes min_bytes=$min_bytes"
  exit 2
fi
if (( size < min_bytes )); then
  echo "valid=false reason=too_small file=$file size=$size min_bytes=$min_bytes"
  exit 5
fi

kind="$(file -b "$file")"
echo "file=$file"
echo "kind=$kind"
echo "size=$size"

case "$expect" in
  zip)
    [[ "$(file -b --mime-type "$file")" == "application/zip" ]] || {
      echo "valid=false reason=mime_mismatch expect=application/zip"
      exit 6
    }
    unzip -t "$file" >/dev/null
    ;;
  docx)
    unzip -t "$file" >/dev/null
    unzip -l "$file" | grep -q 'word/document.xml'
    unzip -Z1 "$file" | grep -Fxq '[Content_Types].xml'
    ;;
  pptx)
    unzip -t "$file" >/dev/null
    unzip -l "$file" | grep -q 'ppt/presentation.xml'
    unzip -Z1 "$file" | grep -Fxq '[Content_Types].xml'
    ;;
  xlsx)
    unzip -t "$file" >/dev/null
    unzip -l "$file" | grep -q 'xl/workbook.xml'
    unzip -Z1 "$file" | grep -Fxq '[Content_Types].xml'
    ;;
  pdf)
    file -b --mime-type "$file" | grep -Eq '^application/pdf$'
    if command -v qpdf >/dev/null 2>&1; then qpdf --check "$file" >/dev/null; fi
    if command -v pdfinfo >/dev/null 2>&1; then pdfinfo "$file" >/dev/null; fi
    ;;
  html)
    file -b --mime-type "$file" | grep -Eq '^text/html$|^text/plain$'
    grep -Eiq '<!doctype html|<html[ >]' "$file"
    ;;
  js)
    file -b --mime-type "$file" | grep -Eq 'javascript|text/plain|application/octet-stream'
    if command -v node >/dev/null 2>&1; then node --check "$file" >/dev/null; fi
    ;;
  image)
    file -b --mime-type "$file" | grep -Eq '^image/'
    ;;
  gif)
    file -b --mime-type "$file" | grep -Eq '^image/gif$'
    ;;
  *)
    echo "unknown expectation: $expect" >&2
    exit 2
    ;;
esac

if ((${#require_entries[@]} > 0)); then
  case "$expect" in
    zip|docx|pptx|xlsx)
      for entry in "${require_entries[@]}"; do
        unzip -Z1 "$file" | grep -Fxq "$entry" || {
          echo "valid=false reason=missing_required_entry entry=$entry"
          exit 7
        }
      done
      ;;
    *)
      echo "valid=false reason=require_entry_only_supported_for_zip_like expect=$expect"
      exit 2
      ;;
  esac
fi

sha256="$(sha256sum "$file" | awk '{print $1}')"
echo "sha256=$sha256"
echo "valid=true expect=$expect"
