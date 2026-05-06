# Repo Usage

Use this repo for reusable workflows that are likely to be used across multiple incidents, repos, or agent sessions.

Promotion path:
- draft in `~/.AGENTS-temp/agent-skills/`
- promote into `~/git/agent-skills/skills/<skill>/`
- expose globally through `~/.codex/skills/<skill>`

Use a skill when:
- the workflow repeats
- the commands are fragile or easy to get wrong
- the same investigation or remediation pattern appears more than once

Do not use this repo for:
- real application or infrastructure implementation code
- one-off incident evidence
- large raw outputs
- temporary handoff notes

Keep those in:
- the real repo for implementation
- `~/.AGENTS-temp/<repo>/` for evidence and scratch

Current stable examples in this repo:
- `ecs-monitoring`
- `ecs-recovery`
- `awslogs-investigation`
- `gitlab-triage`
- `repo-summary-and-relation-mapping`
- `ec2-quick-create`
- `ec2-ttl-alert`
- `cis-inspector-scan`
- `cis-ssm-apply-validate`
- `ecs-mixed-ami-canary`
- `imagebuilder-bake-validate`
- `ami-validation-ssm`
- `imagebuilder-component-publish`
- `aws-ssm-run-command` as the core SSM Run Command engine
- `ssm-command-evidence` as the durable evidence wrapper on top of that core
- `s3-artifact-stage-verify`
- `skill-autoresearch-loop`

For long-term skill quality, use a bounded autoresearch loop:
- see `docs/AUTORESEARCH_FOR_SKILLS.md`

Useful repo helpers:
- install one shared skill:
  - `scripts/link-skill.sh <skill-name>`
- install all current shared skills:
  - `scripts/link-all-skills.sh`
- run a lightweight repo check:
  - `scripts/check-skill-repo.sh`
- run repo checks plus all skill smoke tests:
  - `scripts/run-smoke-tests.sh`
- verify all durable skills are exposed through `~/.codex/skills`:
  - `scripts/check-promoted-skills.sh`
