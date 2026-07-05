# AGENTS.md - agent-skills

Purpose:
- keep reusable Codex and operator skills in one durable repo
- separate stable reusable capability from per-run evidence
- avoid leaking one-off lane logic into shared skills

## Role

- durable reusable skills live here
- unstable drafts, raw logs, and autoresearch artifacts stay under:
  - `~/.AGENTS-temp/agent-skills/`
- skill discovery for Codex happens through:
  - `~/.codex/skills/`
- this repo is the durable source, not the direct discovery path
- external/direct installed skills that are not source-owned here are tracked in:
  - `docs/EXTERNAL_LOCAL_SKILLS.md`

## Working rules

- prefer workflow generalization and stable interfaces over repo-specific
  execution detail
- create or update small and clear skills directly under:
  - `skills/<skill>/`
- use incubation under `~/.AGENTS-temp/agent-skills/` when the skill is rough,
  likely to be discarded, or needs autoresearch first
- expose only stable, proven skills globally
- keep repo-specific policy in the owning repo, not in shared skills

## Promotion path

1. create or refine the skill in:
   - `skills/<skill>/`
2. expose it through:
   - `~/.codex/skills/<skill>`
3. keep one-off evidence and generated outputs out of the repo
4. for a new machine such as office WSL:
   - run `scripts/bootstrap-local-skills.sh`
   - read `docs/OFFICE_MIGRATION.md`

## Git sharing model

- Treat git here as backup and shared learning first.
- Direct push to `main` is allowed for small additive skill/docs changes after
  validation.
- Use a branch or PR for:
  - deleting or renaming skills
  - changing shared scripts
  - restructuring repo layout
  - generated or bulk file changes
  - broad multi-skill changes
  - changes from an external agent that has not been reviewed yet
- Never delete or rename existing skills or scripts without explicit Amit
  approval.
- Before commit or push, run:
  - `scripts/check-skill-repo.sh`
  - `git diff --check`
- Do not force-push unless Amit explicitly asks.

## File model

- `AGENTS.md` = stable repo rules
- `README.md` = human repo overview and promotion model
- `PLANS.md` = active repo work when needed
- `skills/` = durable shared skills
- `scripts/` = repo helpers for linking, checking, and smoke validation

## Compact rule

- for low-context restart, prefer:
  1. `~/.AGENTS-temp/agent-skills/COMPACT_RESUME_CURRENT.md`
  2. `README.md`
  3. `PLANS.md` only if directly relevant

## Safety

- do not put secrets in skill files
- do not turn one-off incident notes into shared skills
- keep stable interfaces short and reviewable
