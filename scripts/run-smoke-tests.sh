#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/git/agent-skills}"

if [[ ! -d "$ROOT/skills" ]]; then
  echo "skills directory not found: $ROOT/skills" >&2
  exit 1
fi

cd "$ROOT"

echo "== repo shape =="
bash scripts/check-skill-repo.sh "$ROOT"

echo
echo "== shell syntax =="
find scripts skills -type f -name '*.sh' -print0 \
  | sort -z \
  | xargs -0 -r -n1 bash -n
echo "shell syntax ok"

echo
echo "== yaml parse =="
yaml_files=()
while IFS= read -r -d '' path; do
  yaml_files+=("$path")
done < <(find skills \( -path '*/agents/*.yaml' -o -name '*.yml' -o -name '*.yaml' \) -print0 | sort -z)

if [[ "${#yaml_files[@]}" -gt 0 ]]; then
  python3 - "${yaml_files[@]}" <<'PY'
import sys
import yaml

for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as fh:
        yaml.safe_load(fh)
    print(f"OK {path}")
PY
else
  echo "no yaml files found"
fi

echo
echo "== skill smoke tests =="
found=0
while IFS= read -r -d '' test_script; do
  found=1
  echo "-- $test_script"
  bash "$test_script"
done < <(find skills -path '*/tests/*.sh' -type f -print0 | sort -z)

if [[ "$found" -eq 0 ]]; then
  echo "no skill smoke tests found"
fi

echo
echo "all smoke checks passed"
