# Promotion Flow

Promote something into this repo when:
- it has been reused at least twice, or
- it is clearly a stable workflow that should be reused

Default fast path:
1. create or update the durable skill under `~/git/agent-skills/skills/<skill>/`
2. simplify hardcoded values
3. keep only the reusable parts
4. write or update `SKILL.md`
5. move supporting scripts into `scripts/`
6. add `references/` only if the skill needs them
7. expose the skill through `~/.codex/skills/<skill>`

Optional scratch path:
1. incubate rough drafts, generated evidence, or autoresearch output under
   `~/.AGENTS-temp/agent-skills/`
2. promote only the durable reusable parts into
   `~/git/agent-skills/skills/<skill>/`
3. expose the skill through `~/.codex/skills/<skill>`

Do not promote:
- raw logs
- one-off reports
- temporary prompts
- duplicate README-heavy scratch structures
