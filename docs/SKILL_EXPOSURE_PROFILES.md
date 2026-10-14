# Skill Exposure Profiles

Keep reusable skill source in this repository and expose only the smallest set
needed by the current Codex workflow. Disabling exposure never deletes source.

## Two user-facing presets (source-only until explicitly applied)

| Selection | Resolved existing profiles | Enabled source-owned skills |
| --- | --- | --- |
| `default` (AWS-first) | `global-core` + `aws-daily` | `safe-shell-ops`, `amit-operator-commands`, `ci-operator`, `aws-private-network-preflight`, `aws-ssm-run-command` |
| `no-aws` | `global-core` | `safe-shell-ops`, `amit-operator-commands`, `ci-operator` |

These are **aliases**, not duplicated profile files. The existing `global-core` and `aws-daily` lists remain authoritative. Default AWS skill **discovery is not AWS execution approval**; repository and account safety gates still apply. `web-html-page`, `visual-explainer`,
`aws-architecture-diagram`, and `deep-work` are disabled by default and remain
available for an exact task.

The wider `aws-ops`, `html-reporting`, and `worker-control` profiles are
explicit opt-ins. Plugin-provided and bundled system skills are a separate
layer and are not changed by this repository's profile controller.

## How it works

`scripts/apply-skill-profile.py` owns one marked block in the local Codex
configuration. It records every source-owned skill with an explicit enabled or
disabled value. It also creates missing discovery links for enabled skills but
does not unlink disabled skills or touch external entries.

The controller:

- defaults to dry-run;
- refuses source-owned overrides outside its managed block;
- preserves unrelated configuration and external skill entries;
- writes a mode-600 backup and action record before mutation;
- uses atomic configuration replacement;
- refuses rollback after unrelated configuration drift; and
- never restarts Codex.

Codex requires a restart after a skill enablement change. Perform that restart
only at an approved idle boundary.

## Preview and apply

Preview AWS-first default (no changes):

```bash
scripts/apply-skill-profile.py --profile default
```

Preview non-AWS core (no changes):

```bash
scripts/apply-skill-profile.py --profile no-aws
```

Apply only at an approved idle/adoption boundary:

```bash
scripts/apply-skill-profile.py --profile default --apply
# or
scripts/apply-skill-profile.py --profile no-aws --apply
```

Legacy explicit `--profile global-core --profile aws-daily` remains supported.

Enable one specialist while retaining the selected base profile:

```bash
scripts/apply-skill-profile.py \
  --profile global-core \
  --enable aws-architecture-diagram \
  --apply
```

An exact `--disable` removes a skill from the selected profile set:

```bash
scripts/apply-skill-profile.py \
  --profile global-core \
  --disable amit-operator-commands
```

## Restore

Apply mode writes a private record under the profile-apply evidence directory.
Preview restoration first:

```bash
scripts/apply-skill-profile.py --restore-record <record.json>
```

Restore after review:

```bash
scripts/apply-skill-profile.py --restore-record <record.json> --apply
```

Restore is fail-closed: it verifies both the applied configuration checksum and
the backup checksum before changing anything.

## Bootstrap

The bootstrap helper **applies AWS-first `default`** when run with no arguments:

```bash
scripts/bootstrap-local-skills.sh
```

For core-only non-AWS mode, select `no-aws` explicitly:

```bash
scripts/bootstrap-local-skills.sh no-aws
```

Both commands mutate local Codex config/links; neither is a harmless review. Existing explicit profile combinations continue to work.

The bootstrap does not link every source skill and does not create or update
Agent Share or Agent Web directories.

## Validation boundaries

The profile controller manages source-owned discovery and enablement only. It
does not prove invocation, project authorization, or a successful runtime
restart. Validate effective discovery in a fresh session after an approved
restart. Keep credentials, authentication state, plugin caches, and unrelated
configuration outside the controller's scope.

Official references:

- [OpenAI skill guide](https://developers.openai.com/codex/skills)
- [OpenAI Codex configuration reference](https://developers.openai.com/codex/config-reference)
