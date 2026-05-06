#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/git/agent-skills}"
SKILLS_ROOT="$ROOT/skills"

if [[ ! -d "$SKILLS_ROOT" ]]; then
  echo "skills directory not found: $SKILLS_ROOT" >&2
  exit 1
fi

errors=0
checked=0

while IFS= read -r -d '' skill_dir; do
  skill_name="$(basename "$skill_dir")"
  checked=$((checked + 1))
  echo "check $skill_name"

  if [[ ! -f "$skill_dir/SKILL.md" ]]; then
    echo "  error: missing SKILL.md"
    errors=$((errors + 1))
  fi

  if [[ ! -f "$skill_dir/agents/openai.yaml" ]]; then
    echo "  error: missing agents/openai.yaml"
    errors=$((errors + 1))
  fi

  while IFS= read -r -d '' script_path; do
    if ! bash -n "$script_path"; then
      echo "  error: bash syntax check failed: $script_path"
      errors=$((errors + 1))
    fi
  done < <(find "$skill_dir/scripts" -type f -name '*.sh' -print0 2>/dev/null)
done < <(find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

echo
echo "checked=$checked errors=$errors"

if [[ "$errors" -gt 0 ]]; then
  exit 1
fi
