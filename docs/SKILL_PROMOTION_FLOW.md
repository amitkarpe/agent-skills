# Skill Promotion Flow

Use this as the default lifecycle for shared local skills.

## Goal

Keep rough experimentation separate from durable reusable skills, and keep
Codex discovery separate from the source repo.

## Three stages

1. Draft / incubate
   - path:
     - `~/.AGENTS-temp/agent-skills/`
   - use for:
     - scratch workflows
     - autoresearch outputs
     - trial scripts
     - unstable drafts

2. Durable source
   - path:
     - `~/git/agent-skills/skills/<skill>/`
   - use for:
     - reusable skill definition
     - `SKILL.md`
     - helper scripts
     - optional agent metadata

3. Global install / discovery
   - path:
     - `~/.codex/skills/<skill>`
   - purpose:
     - make the skill visible to Codex across repos

## Discovery rule

Codex does not discover skills directly from `~/git/agent-skills/`.

The live discovery path is:

- `~/.codex/skills/`

Recommended install method:

- symlink `~/.codex/skills/<skill>` to `~/git/agent-skills/skills/<skill>`
- install one skill with:
  - `~/git/agent-skills/scripts/link-skill.sh <skill-name>`
- or use:
  - `~/git/agent-skills/scripts/link-all-skills.sh`

This keeps one durable source repo while making the skill visible everywhere.

## Promotion rule

Move a draft into `agent-skills` when:

- it has been used in real work
- it saves time or tokens
- the loop is reusable
- the interface is stable enough to document

Install it into `~/.codex/skills` when:

- it is good enough for cross-repo use
- you want Codex to call it by name from any repo
- it passes a lightweight repo check:
  - `~/git/agent-skills/scripts/check-skill-repo.sh`

## Ownership rule

- `agent-skills` owns shared operator mechanics
- each working repo owns its own policy, decisions, and runbooks
- do not put lane-specific policy into shared skills

## Current proven examples

These are already following the model:

- `ecs-mixed-ami-canary`
- `ssm-command-evidence`
- `s3-artifact-stage-verify`

They were first shaped during live AWS work, promoted into
`~/git/agent-skills/skills/`, and then exposed under `~/.codex/skills/` for
cross-repo reuse.
