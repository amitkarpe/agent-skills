#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "usage: $0 <skill-name> [source-root] [dest-root]" >&2
  exit 1
fi

SKILL_NAME="$1"
SRC_ROOT="${2:-$HOME/git/agent-skills/skills}"
DEST_ROOT="${3:-$HOME/.codex/skills}"

SRC_PATH="$SRC_ROOT/$SKILL_NAME"
DEST_PATH="$DEST_ROOT/$SKILL_NAME"

if [[ ! -d "$SRC_PATH" ]]; then
  echo "skill not found: $SRC_PATH" >&2
  exit 1
fi

if [[ ! -f "$SRC_PATH/SKILL.md" ]]; then
  echo "missing SKILL.md: $SRC_PATH/SKILL.md" >&2
  exit 1
fi

mkdir -p "$DEST_ROOT"

if [[ -L "$DEST_PATH" ]]; then
  current_target="$(readlink -f "$DEST_PATH" || true)"
  desired_target="$(readlink -f "$SRC_PATH")"
  if [[ "$current_target" == "$desired_target" ]]; then
    echo "already linked: $DEST_PATH -> $desired_target"
    exit 0
  fi
  rm -f "$DEST_PATH"
elif [[ -e "$DEST_PATH" ]]; then
  echo "destination exists and is not a symlink: $DEST_PATH" >&2
  exit 1
fi

ln -s "$SRC_PATH" "$DEST_PATH"
echo "linked: $DEST_PATH -> $SRC_PATH"
