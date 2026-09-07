# agent-skills

Canonical local repo for reusable Codex/OpenAI-style skills.

## Purpose

- keep reusable workflows out of one-off incident lanes
- share stable skills across Codex, AWS Q, and future agents
- separate reusable capability from per-run evidence

## Working model

- durable reusable skills live here
- small or clear skills can be created directly under `skills/<skill>/`
- rough or experimental skills can incubate under `~/.AGENTS-temp/agent-skills/`
- extra scripts, raw outputs, one-off docs, reports, and scratch stay under `~/.AGENTS-temp/<repo>/`
- real implementation code stays in the real repo, not here

## Promotion path

Source promotion and installed discovery are separate decisions:

1. Create or refine reusable source under `skills/<skill>/`; incubate rough
   work outside the repository when necessary.
2. Validate the source, then separately approve where it should be discoverable.
3. Follow [Skill Exposure Profiles](docs/SKILL_EXPOSURE_PROFILES.md) for the
   source/discovery/invocation distinction, protected skills and reversible
   single-skill trials. Do not install everything merely because source exists.

Existing helpers remain available, not automatic startup steps:

- `scripts/link-skill.sh`: link one selected skill after target verification.
- `scripts/link-all-skills.sh` and `scripts/bootstrap-local-skills.sh`: bulk
  installation; not a lean-discovery or review default.
- `scripts/skill-inventory.py`: source/filesystem inventory, not runtime proof.
- `scripts/check-skill-repo.sh`: source shape validation.
- `scripts/run-smoke-tests.sh`: existing complete source smoke checks.
- `scripts/check-promoted-skills.sh`: checks an all-source-skills-linked
  installation, not a selectively enabled runtime.

Helpers default to `~/.codex/skills/`; verify the installed Codex loader rather
than treating that historical path as universal. Do not migrate directories or
change discovery links as part of a documentation review. Remote Git merge is
not deployment; pulling a clone already behind live symlinks can change what
agents load, so even that update needs the host's approved adoption scope.

For an explicitly approved migration, inspect `docs/OFFICE_MIGRATION.md` and
current helper behavior. Maintainer responsibilities are in
`docs/A_OWNERSHIP_AND_OFFICE_SKILL_SYSTEM.md`; a normal skills task does not
require Agent Share or a report service.

## When To Promote

Create directly in `agent-skills` when:

- the workflow is small and easy to review
- the command surface is already clear
- the skill can pass repo checks without a separate scratch harness
- the change should be versioned immediately

Use `~/.AGENTS-temp/agent-skills/` first when:

- the skill may be thrown away
- the workflow needs autoresearch or a harness
- generated outputs, raw logs, or experiments are expected
- the first draft would create noisy repo churn

Promote a temp draft into `agent-skills` when:

- the same operator loop repeated at least `2-3` times
- the workflow clearly saves time or tokens
- the inputs/outputs are stable enough to describe
- the logic is reusable across repos

Expose a skill through a verified Codex discovery root when:

- the skill already proved useful in real work
- the interface is stable enough for reuse
- you want other repos to call it by name without local repo copies

## Current skills

- `skills/ecs-monitoring/`
- `skills/ecs-recovery/`
- `skills/awslogs-investigation/`
- `skills/gitlab-triage/`
- `skills/repo-summary-and-relation-mapping/`
- `skills/ec2-quick-create/`
- `skills/ec2-ttl-alert/`
- `skills/cis-inspector-scan/`
- `skills/cis-ssm-apply-validate/`
- `skills/terraform-terragrunt-cleanup/`
- `skills/ecs-mixed-ami-canary/`
- `skills/aws-ec2-ami-cleanup-inventory/`
- `skills/ops-scan-candidate-selection/`
- `skills/imagebuilder-bake-validate/`
- `skills/ami-validation-ssm/`
- `skills/imagebuilder-component-publish/`
- `skills/s3-artifact-stage-verify/`
- `skills/aws-ssm-run-command/` (core SSM Run Command engine)
- `skills/ssm-command-evidence/` (durable evidence wrapper)
- `skills/skill-autoresearch-loop/`
- `skills/amit-operator-commands/`
- `skills/linux-backup-to-s3/`
- `skills/plan-decision-form/`

## Skill shape

- required:
  - `SKILL.md`
- usually:
  - `scripts/`
- optional:
  - `references/`
  - `assets/`
  - `agents/openai.yaml`

Repo-level usage notes live in `docs/`.
