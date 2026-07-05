#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SRC_ROOT="${1:-$REPO_ROOT/skills}"
DEST_ROOT="${2:-$CODEX_HOME/skills}"

echo "agent-skills bootstrap"
echo "home:       $HOME"
echo "repo:       $REPO_ROOT"
echo "source:     $SRC_ROOT"
echo "dest:       $DEST_ROOT"
echo

"$REPO_ROOT/scripts/check-skill-repo.sh" "$REPO_ROOT"
echo

"$REPO_ROOT/scripts/link-all-skills.sh" "$SRC_ROOT" "$DEST_ROOT"
echo

"$REPO_ROOT/scripts/check-promoted-skills.sh" "$SRC_ROOT" "$DEST_ROOT"

echo
echo "done: shared skills are linked into $DEST_ROOT"
