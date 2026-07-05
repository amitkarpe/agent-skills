#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SRC_ROOT="${1:-$REPO_ROOT/skills}"
DEST_ROOT="${2:-$CODEX_HOME/skills}"
SHARE_ROOT="${AGENT_SHARE_ROOT:-/opt/agent-share}"
SHARE_SKILLS_LINK="$SHARE_ROOT/skills"

link_agent_share_skills() {
  if [[ ! -d "$SHARE_ROOT" ]]; then
    echo "agent-share: skip (not present: $SHARE_ROOT)"
    return 0
  fi

  if [[ ! -w "$SHARE_ROOT" ]]; then
    echo "agent-share: skip (not writable: $SHARE_ROOT)"
    return 0
  fi

  if [[ -L "$SHARE_SKILLS_LINK" ]]; then
    local current_target desired_target
    current_target="$(readlink -f "$SHARE_SKILLS_LINK" || true)"
    desired_target="$(readlink -f "$SRC_ROOT")"
    if [[ "$current_target" == "$desired_target" ]]; then
      echo "agent-share: already linked: $SHARE_SKILLS_LINK -> $desired_target"
      return 0
    fi
    rm -f "$SHARE_SKILLS_LINK"
  elif [[ -e "$SHARE_SKILLS_LINK" ]]; then
    echo "agent-share: skip (destination exists and is not a symlink: $SHARE_SKILLS_LINK)"
    return 0
  fi

  ln -s "$SRC_ROOT" "$SHARE_SKILLS_LINK"
  echo "agent-share: linked: $SHARE_SKILLS_LINK -> $SRC_ROOT"
}

echo "agent-skills bootstrap"
echo "home:       $HOME"
echo "repo:       $REPO_ROOT"
echo "source:     $SRC_ROOT"
echo "dest:       $DEST_ROOT"
echo "share:      $SHARE_ROOT"
echo

"$REPO_ROOT/scripts/check-skill-repo.sh" "$REPO_ROOT"
echo

"$REPO_ROOT/scripts/link-all-skills.sh" "$SRC_ROOT" "$DEST_ROOT"
echo

"$REPO_ROOT/scripts/check-promoted-skills.sh" "$SRC_ROOT" "$DEST_ROOT"
echo

link_agent_share_skills

echo
echo "done: shared skills are linked into $DEST_ROOT"
