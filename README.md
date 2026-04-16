# agent-skills

Canonical local repo for reusable Codex/OpenAI-style skills.

## Purpose

- keep reusable workflows out of one-off incident lanes
- share stable skills across Codex, AWS Q, and future agents
- separate reusable capability from per-run evidence

## Working model

- durable reusable skills live here
- incubating local skills start under `~/.AGENTS-temp/skills/`
- extra scripts, raw outputs, one-off docs, reports, and scratch stay under `~/.AGENTS-temp/<repo>/`
- real implementation code stays in the real repo, not here

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
