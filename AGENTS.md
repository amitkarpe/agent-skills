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

## Policy and transport ownership

Skills own reusable workflow interfaces and deterministic helpers, not general
policy, concrete model defaults, private lane bindings or controller history.
Read the owning repository's approval/goal first; use the selected shared policy
for testing and temporary-state lifecycle and the vendor adapter for model choice.

For verified persistent Codex sessions, adopt the
[native queue protocol](https://github.com/amitkarpe/agent-os/blob/535be4b923cb996d85613d970159d71499ad75ae/kb/playbooks/delegation/codex-native-controller-worker-protocol.md).
Use queue for controller-to-worker, worker-to-worker and result messages. A
receipt is transport admission only, never permission to send another copy.
Tmux is lifecycle/observation, not composer, Enter/F12 or supervisor delivery.
The protocol owns blocked-transport reconciliation and the one-redispatch bound.

GitHub reviews and edits follow the owning repository's collaboration authority
or the adopted [public collaboration protocol](https://github.com/amitkarpe/agent-os/blob/535be4b923cb996d85613d970159d71499ad75ae/kb/playbooks/integrations/chatgpt-codex-collaboration-protocol.md).
Do not use browser-oracle for this workflow. Reuse the owning Issue/PR and retain
explicit EDIT/no-merge limits; no skill can widen them.

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

Read this `AGENTS.md` first, then the named active goal/result and `README.md`
only as needed. Read `PLANS.md` only for relevant current work. A historical
resume file is context, never authority or proof of a running service. Do not
create a lane or mandatory artifact set for a tiny direct task.

## Safety

- do not put secrets in skill files
- do not turn one-off incident notes into shared skills
- keep stable interfaces short and reviewable
