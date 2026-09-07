# Standing Maintainer and Skill-System Ownership

This retained document describes roles, not current host/session bindings.
Private paths, controller identity and deployment targets belong in the owning
host profile or runtime registry, not this public repository.

## Ownership

- The user/controller owns priorities, approvals, acceptance, merge decisions
  and whether a capability becomes globally available.
- The standing maintainer owns reusable skills, their interfaces, install
  profiles and repository validation. Implement changes in the owning repo.
- Shared policy and its deployment belong to the selected policy repository;
  the installed vendor-neutral layer is not another skill source.
- Vendor adapters own runtime/model configuration. Execution repositories own
  product code, tests, runbooks, workload gates and private evidence.
- Agent OS owns sanitized reusable explanations. Its guidance cannot override
  project approval or expose private source material.

A neutral shared workspace is optional compatibility state, not a second
implementation tree, policy archive or Codex inbox. A skills-only task must not
require report publishing, a browser profile or a web service.

## Sources and loading

Read [repository guidance](../AGENTS.md), the current approved goal and only the
relevant [README](../README.md) or skill entrypoint. The goal/private registry
supplies exact runtime and evidence paths. Do not recreate a missing host tree
from memory or load every provider's instructions on startup.

`skills/` is the reusable source; native skill-discovery links are installed by
existing repository helpers. Use [external skill records](EXTERNAL_LOCAL_SKILLS.md)
for separately installed capability. Do not copy private or external skills here
without explicit promotion/publication approval.

## Communication

Adopt the [native queue protocol](https://github.com/amitkarpe/agent-os/blob/535be4b923cb996d85613d970159d71499ad75ae/kb/playbooks/delegation/codex-native-controller-worker-protocol.md)
for verified persistent Codex messages in all directions. Results and exact
`Reply-To` remain durable/explicit; shared-directory inboxes and terminal keys
are not an alternative transport. Non-Codex consumers require their own approved
adapter. Do not remove an existing inbox, link or consumer without live evidence
and a separate approved change.

## Installation and validation

Only an explicit installation goal authorizes running
[bootstrap-local-skills.sh](../scripts/bootstrap-local-skills.sh) or changing
discovery links. A normal review does not reinstall every skill.

Use existing checks appropriate to the change:

- [check-skill-repo.sh](../scripts/check-skill-repo.sh) for repository shape;
- [check-promoted-skills.sh](../scripts/check-promoted-skills.sh) when promotion
  or the installed/discovered contract changes;
- focused existing skill checks for changed execution behavior.

Preserve stable skill interfaces and explicit optional installs. Do not promote
rough drafts or change discovery merely because a new machine is available.
Optional compatibility links created by the existing bootstrap are not proof
that a shared workspace or report service is required for ordinary skills work.

## Reports and retention

When reporting is explicitly requested, use the selected report skill and the
host-owned publishing contract. Validate the actual artifact and approved
output destination. Do not store generated reports or operational logs here.

Keep only necessary compatibility pointers in a neutral workspace. Its state
follows the approved goal's acceptance/disposition lifecycle, not a permanent
archive or an independent cleanup timer. Preserve active, dirty, held and unknown
work; do not delete directories or stop services from these instructions.

Never automatically migrate credentials, auth JSON, keys, cloud tokens, raw
evidence, temporary-state roots, report dumps or experimental skills. Required
backups and source/connector approval remain the owning environment's controls.

## Completion

Report the skill/interface changed, existing checks actually run, approved
promotion state and remaining blocker. Verify host links/discovery only when
that installation was in scope. Missing optional report/shared-workspace state
is not a blocker for a skills-only change; a required missing dependency is.
Do not claim migration, service health or cleanup from a documentation merge.
