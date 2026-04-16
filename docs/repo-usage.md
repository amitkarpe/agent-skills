# Repo Usage

Use this repo for reusable workflows that are likely to be used across multiple incidents, repos, or agent sessions.

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
