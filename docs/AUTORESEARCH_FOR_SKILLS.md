# Autoresearch for skills

Use a bounded autoresearch loop to improve one skill at a time.

Reusable scaffold:

- `skills/skill-autoresearch-loop/`
- initialize a workspace with:
  - `bash skills/skill-autoresearch-loop/scripts/init-autoresearch-workspace.sh <repo> <skill> [metric]`

Core pattern:

1. Choose one skill and one narrow metric.
2. Freeze a small test harness with 3-5 repeatable scenarios.
3. Make one candidate improvement to `SKILL.md`, scripts, or defaults.
4. Re-run the same harness and compare results.
5. Keep the change only if the metric improves without increasing risk.

Good metrics for local skills:

- fewer manual commands
- higher first-try success rate
- lower time to valid result
- fewer repo-specific edits per run
- better evidence output under `~/.AGENTS-temp/<repo>/`

Rules:

- optimize one skill at a time
- keep the metric explicit
- do not use production mutation as the first harness
- prefer bake/validate/test loops over live rollout loops
- save experiment artifacts outside this repo

Recommended first candidates:

- `imagebuilder-bake-validate`
- `ami-validation-ssm` if extracted
- `ecs-rollout-validation` if extracted
- `cis-override-decision` if extracted
