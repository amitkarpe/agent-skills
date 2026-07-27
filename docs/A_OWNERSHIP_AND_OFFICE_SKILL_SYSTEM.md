# A Ownership And Office Skill System

Status: active
Owner role: `A` agent
Controller role: `Q`

## Purpose

This document defines how shared skills, shared context, and local web/report
tools should move from the home host to office WSL without losing the rules we
learned.

The goal is not to copy everything blindly. The goal is to make office able to
run the same controller/worker system from clean, deterministic sources.

## Ownership Model

`Q` owns decisions:

- priorities
- safety gates
- final approval
- repo merge decisions
- whether a skill becomes global/default

`A` owns the agent system:

- `agent-skills` repo hygiene
- skill bootstrap and validation
- skill install profiles
- `/opt/agent-share` context and communication contracts
- `/opt/agent-web` report/app publishing rules
- drift checks between home and office

`B` and other workers consume the system:

- read shared contracts
- use installed skills
- write messages through `/opt/agent-share/agents`
- publish reports through deterministic wrappers
- do not change shared rules unless Q or A asks

## Canonical Sources

Skills source repo:

```text
~/git/agent-skills/
```

Codex live discovery path:

```text
~/.codex/skills/
```

Shared cross-agent context:

```text
/opt/agent-share/
```

Local web apps and reports:

```text
/opt/crypto-web/fast/   fast reports
/opt/crypto-web/demos/  visual reports and demos
/opt/crypto-web/deep/   durable deep dashboards
```

`/opt/agent-web/AGENTS.md` is authoritative for publishing paths and URLs.

## Default Install Rule

Default install means:

- all stable skills under `agent-skills/skills/`
- symlinked into `~/.codex/skills/`
- validated by:
  - `scripts/check-skill-repo.sh`
  - `scripts/check-promoted-skills.sh`

Do not install rough drafts from:

```text
~/.AGENTS-temp/agent-skills/
```

Do not copy external/private skills into this repo unless Q approves promotion.

## Optional Skill Rule

Optional skills are allowed, but they must be explicit.

Examples:

- external curated skills installed by Codex plugins
- user-local emergency skills
- repo-specific nested skills
- experimental A/B/Hermes drafts

Optional skills should be documented in:

```text
docs/EXTERNAL_LOCAL_SKILLS.md
```

They should not be silently copied into office.

## Office Bootstrap

Run on office:

```bash
cd ~/git/agent-skills
git pull --ff-only
scripts/bootstrap-local-skills.sh
```

The bootstrap does three things:

1. checks the repo skill shape;
2. links stable skills into `~/.codex/skills`;
3. if `/opt/agent-share` exists and is writable, links:

```text
/opt/agent-share/skills -> ~/git/agent-skills/skills
```

This matters because home used an absolute symlink to `/home/dev/...`; office
must point at `/home/user/...`.

## A Startup Checklist

When A starts on office, read:

1. `~/git/agent-skills/AGENTS.md`
2. `~/git/agent-skills/README.md`
3. this file
4. `/opt/agent-share/agents/COMMUNICATION_CONTRACT.md`
5. `/opt/agent-web/AGENTS.md`
6. `/opt/agent-share/ai/opencode/OPENCODE.md`

Then run:

```bash
cd ~/git/agent-skills
scripts/bootstrap-local-skills.sh
/opt/agent-share/bin/report-agent validate
```

If `/opt/agent-share` or `/opt/agent-web` is missing on office, A should report
that as a migration gap. Do not recreate the full tree from memory.

## Report/Web Contract

Agents must not write reports directly under:

```text
/opt/agent-web/www/reports/
```

Use the surface documented by `/opt/agent-web/AGENTS.md`:

```text
/opt/crypto-web/fast/<slug>/index.html
/opt/crypto-web/demos/<slug>/index.html
/opt/crypto-web/deep/<slug>/index.html
```

## Communication Contract

A/B/Hermes/Q messages use:

```text
/opt/agent-share/agents/COMMUNICATION_CONTRACT.md
```

Minimum body:

```text
ACT:
WATCH:
BLOCKED:
NEXT:
```

Do not create ad hoc communication folders unless the contract is missing.

## What Not To Migrate Automatically

Do not automatically copy:

- secrets
- `.env`
- auth JSON
- SSH keys
- cloud credentials
- raw evidence folders
- `.AGENTS-temp`
- old report dumps
- experimental skills

Amit handles secrets manually.

## Drift Check

On any machine:

```bash
cd ~/git/agent-skills
git status --short --branch
scripts/bootstrap-local-skills.sh
```

Expected:

- repo clean or only intentional edits;
- all stable skills linked;
- promoted-skill check passes;
- `/opt/agent-share/skills` points to the local repo if `/opt/agent-share`
  exists and is writable.

## Completion Standard

Office skill migration is complete only when:

- `agent-skills` is pulled to latest `main`;
- `scripts/bootstrap-local-skills.sh` passes on office;
- Q-office can see shared skills in `~/.codex/skills`;
- `/opt/agent-share/skills` points to the office local repo or is explicitly
  recorded as unavailable;
- report contract validation passes or the missing `/opt/agent-web` state is
  recorded;
- A has a clear next action and no hidden dependency on home-only paths.
