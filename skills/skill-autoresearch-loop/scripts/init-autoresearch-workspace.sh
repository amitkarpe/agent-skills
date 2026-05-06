#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  init-autoresearch-workspace.sh <repo-name> <skill-name> [primary-metric]

Example:
  init-autoresearch-workspace.sh trustdev imagebuilder-bake-validate "first-try success rate"
EOF
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 1
fi

repo_name="$1"
skill_name="$2"
primary_metric="${3:-first-try success rate}"

base_dir="${HOME}/.AGENTS-temp/${repo_name}/autoresearch/${skill_name}"
runs_dir="${base_dir}/runs"

mkdir -p "${runs_dir}"

cat > "${base_dir}/00-goal.md" <<EOF
# Goal

- repo: \`${repo_name}\`
- skill: \`${skill_name}\`
- primary metric: ${primary_metric}

Working rule:
- improve one skill at a time
- keep the harness fixed
- keep only changes that improve the result without adding risk
EOF

cat > "${base_dir}/01-harness.md" <<'EOF'
# Harness

Define 3-5 repeatable scenarios.

For each scenario record:
- prompt or operator ask
- required inputs
- expected outputs
- failure conditions
- evidence path under `runs/`

Keep this file stable while iterating.
EOF

cat > "${base_dir}/02-baseline.md" <<'EOF'
# Baseline

Record the first run before changing the skill.

Suggested fields:
- date/time
- skill version or commit
- scenarios run
- primary metric result
- secondary observations
- obvious failure modes
EOF

cat > "${base_dir}/03-iteration-template.md" <<'EOF'
# Iteration Template

## Change
- what changed

## Why
- hypothesis for improvement

## Harness
- same as baseline: yes/no

## Result
- primary metric
- secondary observations

## Decision
- keep / reject / defer
EOF

cat > "${base_dir}/04-decision-log.md" <<'EOF'
# Decision Log

| Iteration | Change | Metric result | Decision | Notes |
|---|---|---|---|---|
| 0 | baseline | pending | baseline | fill after first run |
EOF

printf '%s\n' "${base_dir}"
