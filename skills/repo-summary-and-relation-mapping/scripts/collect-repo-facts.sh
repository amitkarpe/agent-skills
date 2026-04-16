#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <repo_path> [related_repo_path...]" >&2
  exit 2
fi

TARGET_REPO="$1"
shift || true

if [[ ! -d "$TARGET_REPO" ]]; then
  echo "repo path not found: $TARGET_REPO" >&2
  exit 1
fi

echo "TARGET_REPO=$TARGET_REPO"
echo "REPO_NAME=$(basename "$TARGET_REPO")"
echo "PWD=$PWD"
echo

if git -C "$TARGET_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "=== GIT ==="
  echo "BRANCH=$(git -C "$TARGET_REPO" branch --show-current 2>/dev/null || true)"
  echo "REMOTE_URL=$(git -C "$TARGET_REPO" remote get-url origin 2>/dev/null || true)"
  echo
fi

echo "=== TOP LEVEL ==="
find "$TARGET_REPO" -maxdepth 1 -mindepth 1 | sort
echo

for FILE in README.md ROADMAP.md PLANS.md AGENTS.md AGENTS.override.md; do
  if [[ -f "$TARGET_REPO/$FILE" ]]; then
    echo "=== $FILE ==="
    sed -n '1,120p' "$TARGET_REPO/$FILE"
    echo
  fi
done

if [[ $# -gt 0 ]]; then
  echo "=== RELATED REPOS ==="
  for REPO in "$@"; do
    if [[ -d "$REPO" ]]; then
      echo "--- $(basename "$REPO") => $REPO"
      if git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "BRANCH=$(git -C "$REPO" branch --show-current 2>/dev/null || true)"
        echo "REMOTE_URL=$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
      fi
      find "$REPO" -maxdepth 1 -mindepth 1 | sort | sed -n '1,40p'
      echo
    fi
  done
fi
