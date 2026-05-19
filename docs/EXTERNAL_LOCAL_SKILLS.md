# External Local Skills

Purpose: track installed Codex skills that are available locally but are not
source-owned by this repo.

## Policy

- Amit-owned reusable skills should live under `~/git/agent-skills/skills/`.
- The installed discovery path should normally be a symlink:
  - `~/.codex/skills/<skill> -> ~/git/agent-skills/skills/<skill>`
- Direct installed external skills are allowed under `~/.codex/skills/`, but
  they must be listed here.
- Do not edit external/direct installed skills as if they were source-owned by
  this repo.
- Promote an external skill into `agent-skills` only after reviewing provenance,
  license, size, and whether it is useful as an Amit-owned reusable operator
  skill.

## Current External Direct Skills

As of 2026-05-19, keep these installed skills external/direct:

| Skill | Installed path | Reason to keep external for now |
| --- | --- | --- |
| `refactor-module` | `~/.codex/skills/refactor-module` | IBM metadata; third-party/vendor-style provenance. |
| `terraform-search-import` | `~/.codex/skills/terraform-search-import` | IBM metadata; Terraform 1.14 feature-specific guidance. |
| `terraform-skill` | `~/.codex/skills/terraform-skill` | Larger third-party Claude-oriented skill with its own license and docs. |
| `terraform-style-guide` | `~/.codex/skills/terraform-style-guide` | External HashiCorp-style guidance; not yet proven as an Amit-owned operator skill. |
| `terraform-test` | `~/.codex/skills/terraform-test` | IBM metadata; includes bundled Terraform test references. |

Do not copy these into `~/git/agent-skills/skills/` in a cleanup pass unless
that promotion decision is explicit.
