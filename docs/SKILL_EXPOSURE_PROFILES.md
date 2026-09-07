# Skill Exposure Profiles

Keep reusable source; curate what a particular Codex session can discover.
This guide owns exposure choices, not project approval, runtime configuration,
or the shared acceptance/cleanup policy. No installation action is implicit.

## Three separate concepts

| Concept | Meaning | What it does not prove |
| --- | --- | --- |
| Source retained | `skills/<name>/` remains versioned here | Installed or loaded by any host |
| Installed/discoverable | A supported loader sees a folder/link, subject to effective enablement | Invocation, authorization, or actual prompt inclusion |
| Implicit invocation | `policy.allow_implicit_invocation` controls automatic selection | Removal from initial context or measured token savings |

[OpenAI's skill guide](https://developers.openai.com/codex/skills) describes
metadata-first loading and full instructions on selection. It documents
`allow_implicit_invocation: false` as blocking automatic invocation while keeping
explicit invocation available. It does not explicitly guarantee omission of the
skill description from initial context. Treat that effect as **UNKNOWN for the
installed version**, pending measurement; do not equate explicit-only with disabled.

## Verify the loader, do not rename directories

The same guide lists repository/user `.agents/skills`, admin and system roots,
and supports symlinks. This repository's helpers default to `~/.codex/skills/`.
Inspect actual Codex version, effective home, all applicable discovery roots,
resolved targets and duplicate names. Neither layout proves current host behavior.
`~/.agent` is shared policy, not the plural `.agents` skill-discovery directory.
Do not migrate paths, replace sessions or bootstrap merely to match documentation.

The [configuration reference](https://developers.openai.com/codex/config-reference)
documents `skills.config` enablement overrides. Prefer a supported single-skill
`enabled = false` override when approved and verified; unlike explicit-only,
disabling requires re-enablement before normal use. Confirm the accepted path
locator and effective result on the installed version. A required Codex reload
must wait for an approved idle boundary; do not restart a shared app-server.

## Protected capabilities and candidate scope

Preserve existing AWS, SSM, private-network, Inspector/CIS, shell-safety,
worker-goal and core operator capabilities. Do not make a global-only profile
remove those skills. A task-scoped replacement requires evidence first.

These are task-fit candidates, **not measured low-use findings**. Keep all source.
Do not execute or publish through any candidate merely to test discovery.

| Candidate | Source evidence / reason | Proposed exposure and reversal |
| --- | --- | --- |
| [chatgpt-browser-oracle](../skills/chatgpt-browser-oracle/SKILL.md) | Legacy browser artifacts; normal GitHub review is explicitly excluded | First optional single-skill trial: disabled in ordinary sessions; restore exact prior enablement/link for approved legacy use, retaining explicit-only invocation |
| [deep-work](../skills/deep-work/SKILL.md) | Broad research/architecture triggers produce a host-published learning dashboard | Consider task-scoped exposure for requested dashboards; restore the same entry for that task |
| [web-html-page](../skills/web-html-page/SKILL.md) | Generic summary triggers lead to HTML publishing and legacy retention text | Consider task-scoped exposure for requested HTML; restore the same entry, with owning publication/retention gates still binding |
| [plan-decision-form](../skills/plan-decision-form/SKILL.md) | Requires a local form service; text/TUI is already the small-question default | Consider task-scoped exposure for an explicitly requested form; restore the same entry only with the approved service/target |
| [skill-autoresearch-loop](../skills/skill-autoresearch-loop/SKILL.md) | Specialized metric/harness iteration, not ordinary execution | Consider maintainer-task exposure; restore the same entry for an approved experiment |

The other four candidates are recommendations, not changes to their metadata or
host discovery. Oracle's existing explicit-only metadata remains unchanged.
Missing usage history means UNKNOWN, not permission to remove useful capability.

## Bounded adoption and reversal

1. Read-only first: identify one exact source, discovered path, effective
   enablement, active consumer and prior link/config value. Record only safe
   fields in the existing work record; never copy credentials or whole configs.
2. Obtain approval for one named candidate and one mechanism. Do not combine
   a config toggle and unlink, expand to the candidate list, or touch active work.
3. Prefer supported per-skill enablement. If unavailable, unlink only the exact
   verified source-owned discovery symlink, never its target or a real directory.
   An alias/second loader still exposing it means the result is not proven.
4. Verify actual discovery and protected capabilities after an allowed refresh.
   If refresh needs an unauthorized restart, record BLOCKED and stop.
5. Reverse only the approved delta: restore the exact prior config value (or
   absence) or recorded link target, preserving unrelated changes. Recheck
   discovery; do not rebuild the whole installation to undo one trial.

No source deletion, bulk unlink, new plugin/profile framework, scanner or timer.
No SS/tmux/app-server change, Stow/bootstrap, cloud action or cleanup follows
from this guide. Required backups and safety approvals remain binding.

## Existing helpers and validation limits

The existing `global-core`, `aws-daily`, `aws-ops`, `html-reporting` and
`worker-control` files under `profiles/` are reusable historical selections,
not proof of today's minimal set or permission to apply them.

[skill-inventory.py](../scripts/skill-inventory.py) reports source descriptions
and entries in one destination root. Its `active` flag is filesystem presence,
including possible broken/wrong links, not effective Codex enablement. Its tiers
are built-in suggestions, not measured usage. Supply the verified destination;
check actual runtime discovery separately.

[apply-skill-profile.py](../scripts/apply-skill-profile.py) defaults to dry-run;
its apply mode changes a whole link set and writes an action record after changes.
Use preview only for this single-candidate exercise, not `--apply` or bulk restore.
Do not infer a successful rollback from a record alone.

[check-promoted-skills.sh](../scripts/check-promoted-skills.sh) expects every
source skill to have a matching link. A deliberately unlinked skill can fail
that all-installed contract; do not relink everything to make it green. It does
not check native enablement or prompt inclusion. Source shape/smoke checks and
host adoption checks are separate; reuse the existing validators as applicable.

## Context evidence

Record before/after version, model, workspace, source revision, discovery roots,
effective entries and policy load state using the same observation method.
Report separately: source count, filesystem entries, runtime-discovered entries,
implicit-eligible entries, and prompt metadata characters/tokens only if exposed.
Description lengths are an estimate, not actual prompt tokens. Old conversation
history is not removed by changing discovery. Do not open paid experiment loops
or enable verbose/raw-reasoning capture to obtain a number.

No token saving has been measured here. A smaller relevant discovery set is an
expected benefit only. If the runtime does not expose prompt inclusion/counts,
record that result as UNKNOWN and make no numerical saving claim. Keep the
before/after summary and decision in the existing Issue/PR, not another report.
