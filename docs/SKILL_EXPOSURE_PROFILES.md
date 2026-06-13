# Skill Exposure Profiles

Codex can see many skills, but the startup skill list has a small context
budget. When too many skills are visible, Codex shortens descriptions. The full
`SKILL.md` still loads when a skill is selected, but shortened descriptions can
make implicit skill selection weaker.

This repo keeps the durable skill source under `skills/`. Live Codex discovery
happens through `~/.codex/skills/`, usually as symlinks into this repo.

## Policy

- Keep focused skills separate. Do not merge AWS, ECS, SSM, CIS, Image Builder,
  reporting, and worker-control workflows into mega-skills.
- Curate active exposure instead. A skill can exist in this repo without being
  globally visible in every Codex session.
- Use plugins for packaging and sharing related skills, not for turning many
  workflows into one large skill.
- Keep unstable drafts, raw logs, and per-run evidence under
  `~/.AGENTS-temp/agent-skills/`; that path is not durable skill source.
- Profile application changes live discovery symlinks and requires Amit
  approval. Use dry-run first.

## Profiles

Profile allowlists live under `profiles/`. Each file contains one skill name per
line. Blank lines and comments are ignored.

Current profiles:

- `global-core`: small always-on set for most repo sessions.
- `aws-daily`: smaller AWS/CloudOps set for normal AWS work.
- `aws-ops`: AWS and CloudOps workflows for AWS-heavy lanes.
- `html-reporting`: quick reports, visual explainers, and deep dashboards.
- `worker-control`: controller/worker-loop operations.

## Inventory

Run:

```bash
scripts/skill-inventory.py
```

The inventory reports:

- skill name
- description length
- whether the skill is active in `~/.codex/skills`
- proposed tier
- recommendation

Useful variants:

```bash
scripts/skill-inventory.py --format md
scripts/skill-inventory.py --dest-root ~/.codex/skills
```

## Dry Run

Preview a profile without changing live exposure:

```bash
scripts/apply-skill-profile.py --profile global-core
```

Preview with another profile:

```bash
scripts/apply-skill-profile.py --profile global-core --profile aws-daily
```

The helper prints which source-owned skills would be linked or unlinked. It does
not touch external skills that are not symlinks into this repo.

## Apply Later

Only after Amit approval:

```bash
scripts/apply-skill-profile.py --profile global-core --apply
```

For normal AWS work, combine the always-on core with the daily AWS set:

```bash
scripts/apply-skill-profile.py --profile global-core --profile aws-daily --apply
```

For a full AWS-heavy session, combine the always-on core with all AWS
operations:

```bash
scripts/apply-skill-profile.py --profile global-core --profile aws-ops --apply
```

Apply mode writes a reversible action record under:

```text
~/.AGENTS-temp/agent-skills/profile-apply/
```

Preview a rollback from that record:

```bash
scripts/apply-skill-profile.py --restore-record ~/.AGENTS-temp/agent-skills/profile-apply/<record>.json
```

Run the rollback after approval:

```bash
scripts/apply-skill-profile.py --restore-record ~/.AGENTS-temp/agent-skills/profile-apply/<record>.json --apply
```

Do not apply profiles as part of review-only or planning tasks.
