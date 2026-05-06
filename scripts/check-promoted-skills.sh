#!/usr/bin/env bash
set -euo pipefail

SRC_ROOT="${1:-$HOME/git/agent-skills/skills}"
DEST_ROOT="${2:-$HOME/.codex/skills}"

if [[ ! -d "$SRC_ROOT" ]]; then
  echo "source skills directory not found: $SRC_ROOT" >&2
  exit 1
fi

if [[ ! -d "$DEST_ROOT" ]]; then
  echo "destination skills directory not found: $DEST_ROOT" >&2
  exit 1
fi

errors=0
checked=0

while IFS= read -r -d '' skill_dir; do
  skill_name="$(basename "$skill_dir")"
  dest_path="$DEST_ROOT/$skill_name"
  checked=$((checked + 1))
  echo "check $skill_name"

  if [[ ! -f "$skill_dir/SKILL.md" ]]; then
    echo "  error: source missing SKILL.md"
    errors=$((errors + 1))
  fi

  if [[ ! -f "$skill_dir/agents/openai.yaml" ]]; then
    echo "  error: source missing agents/openai.yaml"
    errors=$((errors + 1))
  fi

  if [[ ! -L "$dest_path" ]]; then
    echo "  error: destination is not a symlink: $dest_path"
    errors=$((errors + 1))
    continue
  fi

  current_target="$(readlink -f "$dest_path" || true)"
  desired_target="$(readlink -f "$skill_dir")"

  if [[ "$current_target" != "$desired_target" ]]; then
    echo "  error: destination points to $current_target"
    echo "  want:  $desired_target"
    errors=$((errors + 1))
  fi
done < <(find "$SRC_ROOT" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

echo
echo "checked=$checked errors=$errors"

if [[ "$errors" -gt 0 ]]; then
  exit 1
fi
