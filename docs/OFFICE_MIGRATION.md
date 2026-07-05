# Office Migration - agent-skills

This repo is the source of shared operator skills. Each machine should clone the
repo and expose skills by symlink into that machine's Codex home.

## Target Layout

On home:

```text
/home/dev/git/agent-skills
/home/dev/.codex/skills/<skill> -> /home/dev/git/agent-skills/skills/<skill>
```

On office WSL:

```text
/home/user/git/agent-skills
/home/user/.codex/skills/<skill> -> /home/user/git/agent-skills/skills/<skill>
```

Do not copy secrets into this repo. Do not copy per-run evidence into this repo.

For A's long-term ownership of skills, `/opt/agent-share`, and
`/opt/agent-web`, read `docs/A_OWNERSHIP_AND_OFFICE_SKILL_SYSTEM.md`.

## Office Bootstrap

Run on office:

```bash
cd ~/git/agent-skills
git pull --ff-only
scripts/bootstrap-local-skills.sh
```

Expected result:

- repo skill check passes
- all stable skills are linked into `~/.codex/skills`
- promoted-skill check passes
- if `/opt/agent-share` exists and is writable, `/opt/agent-share/skills`
  points to this machine's local `agent-skills/skills` directory

## If The Repo Is Missing On Office

Clone from the existing remote:

```bash
mkdir -p ~/git
cd ~/git
git clone <agent-skills-remote-url> agent-skills
cd agent-skills
scripts/bootstrap-local-skills.sh
```

Use the existing remote from home; do not create a new upstream just for office.

## Safe Re-run

The bootstrap is intended to be re-runnable:

- already-correct symlinks are skipped
- wrong symlinks are replaced
- non-symlink destination directories are skipped and reported

If a non-symlink exists under `~/.codex/skills/<skill>`, review it manually
before replacing it.

## What Q-Office Should Tell Amit

After running the bootstrap, report only:

- repo branch and latest commit
- number of linked or skipped skills
- whether `scripts/check-promoted-skills.sh` passed
- any destination conflicts that need manual review
