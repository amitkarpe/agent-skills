# Current Plan

Updated: 2026-04-23

## Repo Status

- repo: `agent-skills`
- role:
  - durable home for reusable operator mechanics
  - not a lane repo
  - not the place for one-off evidence or repo-specific implementation
- current repo drift is expected and legitimate:
  - it reflects accepted improvements proven from `trustdev`, `packer`, and `patching`

## Accepted Stable Changes

- `ecs-monitoring`
  - now saves tighter summaries and timing output
- `ecs-mixed-ami-canary`
  - promoted from real mixed-AMI ECS work
- `cis-ssm-apply-validate`
  - improved around real SSM document and params handling
- `ami-validation-ssm`
  - now records `validation_status` in `summary.json`
- `aws-ssm-run-command`
  - accepted as the core SSM Run Command engine
- `ssm-command-evidence`
  - now acts as the durable evidence wrapper on top of that core
- repo helper/docs improvements are accepted:
  - `docs/SKILL_PROMOTION_FLOW.md`
  - `docs/AUTORESEARCH_FOR_SKILLS.md`
  - `scripts/link-skill.sh`
  - `scripts/link-all-skills.sh`
  - `scripts/check-skill-repo.sh`

## Working Rule

- treat the current skill additions and updates as legitimate
- do not reopen them just because they came from different worker lanes
- prefer real-lane proof over abstract refactor work
- patch skills only when repeated friction is clear
- keep one implementation base when possible, then use thin wrappers

## Current Next Move

1. keep using shared skills first in active repos
2. only refine skills when real usage shows noise or duplication
3. keep `aws-ssm-run-command` as core for plain SSM Run Command work
4. keep `ssm-command-evidence` as the durable wrapper
5. keep `cis-ssm-apply-validate` separate for CIS publish/apply/validate workflows

## Non-Goals

- do not turn this repo into a dump of lane-specific scripts
- do not migrate repo-owned build/runtime logic here
- do not run broad autoresearch loops unless one skill has a clear bounded metric
