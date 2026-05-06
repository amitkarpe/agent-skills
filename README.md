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

Default fast path for reusable skills:

1. create or update under:
   - `~/git/agent-skills/skills/<skill>/`
   - use this for small, clear, or already-proven skills
2. expose globally through:
   - `~/.codex/skills/<skill>`
   - this is the path Codex actually discovers across repos

Optional scratch path for uncertain work:

1. incubate under:
   - `~/.AGENTS-temp/agent-skills/`
   - use this for rough testing, scratch notes, autoresearch, and unstable drafts
2. promote into:
   - `~/git/agent-skills/skills/<skill>/`
   - use this once the skill shape is useful and worth keeping
3. expose globally through:
   - `~/.codex/skills/<skill>`
   - this is the path Codex actually discovers across repos

Important:

- repos do not auto-discover skills directly from `~/git/agent-skills/`
- the live discovery path is `~/.codex/skills/`
- the simplest install method is a symlink:
  - `~/.codex/skills/<skill> -> ~/git/agent-skills/skills/<skill>`
- install one skill:
  - `scripts/link-skill.sh <skill-name>`
- bulk install helper:
  - `scripts/link-all-skills.sh`
- repo sanity check:
  - `scripts/check-skill-repo.sh`
- full smoke check:
  - `scripts/run-smoke-tests.sh`
- promotion check:
  - `scripts/check-promoted-skills.sh`
- only expose stable and actually useful skills globally
- keep repo-specific policy in the owning repo, not in shared skills

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

Expose a skill through `~/.codex/skills` when:

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
- `skills/ecs-mixed-ami-canary/`
- `skills/imagebuilder-bake-validate/`
- `skills/ami-validation-ssm/`
- `skills/imagebuilder-component-publish/`
- `skills/s3-artifact-stage-verify/`
- `skills/aws-ssm-run-command/` (core SSM Run Command engine)
- `skills/ssm-command-evidence/` (durable evidence wrapper)
- `skills/skill-autoresearch-loop/`
- `skills/amit-operator-commands/`
- `skills/linux-backup-to-s3/`

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
