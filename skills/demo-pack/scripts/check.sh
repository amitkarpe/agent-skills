#!/usr/bin/env bash
# Check a demo pack directory: offline pages, artifacts present, sizes sane.
set -euo pipefail
d="${1:?usage: check.sh <demo-dir>}"
fail=0
bad() { echo "FAIL: $*" >&2; fail=1; }

# 1. pages must exist, be static, offline and small
pages=$(find "$d/walkthrough" -name '*.html' 2>/dev/null)
[ -n "$pages" ] || bad "no HTML pages in $d/walkthrough"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  grep -qi '<script' "$f" && bad "$f has <script>"
  grep -Eqi "(src|href)[[:space:]]*=[[:space:]]*[\"']?[[:space:]]*(https?:)?//" "$f" && bad "$f links to the network"
  [ "$(du -k "$f" | cut -f1)" -le 5120 ] || bad "$f over 5 MB"
done <<< "$pages"

# 2. artifacts must exist and be non-empty
[ -n "$(find "$d/png" -name '*.png' -size +0 2>/dev/null | head -1)" ] || bad "no PNGs in $d/png"
for ext in mp4 gif; do
  [ -n "$(find "$d/video" -name "*.$ext" -size +0 2>/dev/null | head -1)" ] || bad "no .$ext in $d/video"
done

# 3. size budget (KB)
kb() { # dir pattern -> total KB (0 if none)
  local n; n=$(find "$d/$1" -type f -name "$2" -exec du -k {} + 2>/dev/null | awk '{s+=$1} END{print s+0}')
  echo "$n"; }
[ "$(kb png '*.png')" -le 5120 ] || bad "PNG total over 5 MB"
[ "$(kb video '*.mp4')" -le 5120 ] || bad "MP4 over 5 MB"
[ "$(kb video '*.gif')" -le 12288 ] || bad "GIF over 12 MB"

[ "$fail" = 0 ] && echo "demo pack OK: $d"
exit "$fail"
