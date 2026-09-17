# Skill Exposure Profiles

Keep reusable skill source in this repository and expose only the smallest set
needed by the current Codex workflow. Disabling exposure never deletes source.

## Approved defaults

| Profile | Enabled source-owned skills |
| --- | --- |
| `global-core` | `safe-shell-ops`, `amit-operator-commands` |
| `aws-daily` | `aws-private-network-preflight`, `aws-ssm-run-command` |

Use `global-core` alone for ordinary work. Combine it with `aws-daily` for
routine AWS work. `web-html-page`, `visual-explainer`,
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

Preview the minimal core:

```bash
scripts/apply-skill-profile.py --profile global-core
```

Apply it:

```bash
scripts/apply-skill-profile.py --profile global-core --apply
```

Preview or apply routine AWS exposure:

```bash
scripts/apply-skill-profile.py \
  --profile global-core \
  --profile aws-daily

scripts/apply-skill-profile.py \
  --profile global-core \
  --profile aws-daily \
  --apply
```

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

The bootstrap helper applies `global-core` by default:

```bash
scripts/bootstrap-local-skills.sh
```

Pass profile names to combine them:

```bash
scripts/bootstrap-local-skills.sh global-core aws-daily
```

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
