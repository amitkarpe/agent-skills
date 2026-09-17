#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

profiles=("$@")
if [[ "${#profiles[@]}" -eq 0 ]]; then
  profiles=(global-core)
fi

profile_args=()
for profile in "${profiles[@]}"; do
  profile_args+=(--profile "$profile")
done

echo "agent-skills bootstrap"
echo "repo: $REPO_ROOT"
echo "profiles: ${profiles[*]}"
echo

"$REPO_ROOT/scripts/check-skill-repo.sh" "$REPO_ROOT"
echo

python3 "$REPO_ROOT/scripts/apply-skill-profile.py" \
  --repo-root "$REPO_ROOT" \
  "${profile_args[@]}" \
  --apply

echo
echo "done: selected profiles are installed and configured"
