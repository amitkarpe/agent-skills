#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/scripts/init-autoresearch-workspace.sh"

bash -n "${SCRIPT}"

repo_name="agent-skills"
skill_name="smoke-skill-autoresearch"
metric="manual commands per run"
base_dir="${HOME}/.AGENTS-temp/${repo_name}/autoresearch/${skill_name}"

rm -rf "${base_dir}"

created_dir="$(bash "${SCRIPT}" "${repo_name}" "${skill_name}" "${metric}")"
[[ "${created_dir}" == "${base_dir}" ]]

test -f "${base_dir}/00-goal.md"
test -f "${base_dir}/01-harness.md"
test -f "${base_dir}/02-baseline.md"
test -f "${base_dir}/03-iteration-template.md"
test -f "${base_dir}/04-decision-log.md"
test -d "${base_dir}/runs"

grep -q "${metric}" "${base_dir}/00-goal.md"
