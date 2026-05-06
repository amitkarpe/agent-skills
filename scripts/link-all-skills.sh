#!/usr/bin/env bash
set -euo pipefail

SRC_ROOT="${1:-$HOME/git/agent-skills/skills}"
DEST_ROOT="${2:-$HOME/.codex/skills}"

if [[ ! -d "$SRC_ROOT" ]]; then
  echo "source skills directory not found: $SRC_ROOT" >&2
  exit 1
fi

mkdir -p "$DEST_ROOT"

linked=0
skipped=0

while IFS= read -r -d '' skill_dir; do
  skill_name="$(basename "$skill_dir")"
  dest_path="$DEST_ROOT/$skill_name"

  if [[ ! -f "$skill_dir/SKILL.md" ]]; then
    echo "skip  $skill_name (missing SKILL.md)" >&2
    skipped=$((skipped + 1))
    continue
  fi

  if [[ -L "$dest_path" ]]; then
    current_target="$(readlink -f "$dest_path" || true)"
    desired_target="$(readlink -f "$skill_dir")"
    if [[ "$current_target" == "$desired_target" ]]; then
      echo "skip  $skill_name (already linked)"
      skipped=$((skipped + 1))
      continue
    fi
    rm -f "$dest_path"
  elif [[ -e "$dest_path" ]]; then
    echo "skip  $skill_name (destination exists and is not a symlink)" >&2
    skipped=$((skipped + 1))
    continue
  fi

  ln -s "$skill_dir" "$dest_path"
  echo "link  $skill_name -> $skill_dir"
  linked=$((linked + 1))
done < <(find "$SRC_ROOT" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

echo
echo "done: linked=$linked skipped=$skipped"
