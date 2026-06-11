#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${AGENT_WEB_SKILL_TARGET:-/home/dev/git/agent-skills/skills/agent-web-reporting}"
MODE="dry-run"

usage() {
  cat >&2 <<'EOF'
Usage:
  scripts/sync-to-agent-skills.sh --dry-run
  scripts/sync-to-agent-skills.sh --apply

Copies the reusable agent-web-reporting skill files from this repo into the
live agent-skills tree. Dry-run is the default.

Target can be overridden with AGENT_WEB_SKILL_TARGET.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --apply)
      MODE="apply"
      shift
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

required=(
  "Makefile"
  "SKILL.md"
  "DESIGN.md"
  "agents"
  "fixtures"
  "scripts"
  "templates"
)

for item in "${required[@]}"; do
  if [[ ! -e "$ROOT_DIR/$item" ]]; then
    echo "missing required source: $item" >&2
    exit 1
  fi
done

rsync_args=(
  -a
  --delete
  --exclude '.git/'
  --exclude '.github/'
  --exclude '.gitignore'
  --exclude 'README.md'
  --exclude 'docs/'
  --exclude 'runs/'
  --exclude 'tmp/'
  --exclude 'node_modules/'
  --exclude '__pycache__/'
)

if [[ "$MODE" == "dry-run" ]]; then
  rsync_args+=(--dry-run --itemize-changes)
fi

if [[ "$MODE" == "apply" ]]; then
  if [[ -w "$TARGET_DIR" ]]; then
    rsync "${rsync_args[@]}" \
      "$ROOT_DIR/Makefile" \
      "$ROOT_DIR/SKILL.md" \
      "$ROOT_DIR/DESIGN.md" \
      "$ROOT_DIR/agents" \
      "$ROOT_DIR/fixtures" \
      "$ROOT_DIR/scripts" \
      "$ROOT_DIR/templates" \
      "$TARGET_DIR/"
  else
    sudo -S -p '' rsync "${rsync_args[@]}" \
      "$ROOT_DIR/Makefile" \
      "$ROOT_DIR/SKILL.md" \
      "$ROOT_DIR/DESIGN.md" \
      "$ROOT_DIR/agents" \
      "$ROOT_DIR/fixtures" \
      "$ROOT_DIR/scripts" \
      "$ROOT_DIR/templates" \
      "$TARGET_DIR/"
    sudo -S -p '' chown -R dev:dev "$TARGET_DIR"
  fi
else
  if [[ -r "$TARGET_DIR" && -x "$TARGET_DIR" ]]; then
    rsync "${rsync_args[@]}" \
      "$ROOT_DIR/Makefile" \
      "$ROOT_DIR/SKILL.md" \
      "$ROOT_DIR/DESIGN.md" \
      "$ROOT_DIR/agents" \
      "$ROOT_DIR/fixtures" \
      "$ROOT_DIR/scripts" \
      "$ROOT_DIR/templates" \
      "$TARGET_DIR/"
  else
    sudo -S -p '' rsync "${rsync_args[@]}" \
      "$ROOT_DIR/Makefile" \
      "$ROOT_DIR/SKILL.md" \
      "$ROOT_DIR/DESIGN.md" \
      "$ROOT_DIR/agents" \
      "$ROOT_DIR/fixtures" \
      "$ROOT_DIR/scripts" \
      "$ROOT_DIR/templates" \
      "$TARGET_DIR/"
  fi
fi

echo "mode: $MODE"
echo "source: $ROOT_DIR"
echo "target: $TARGET_DIR"
