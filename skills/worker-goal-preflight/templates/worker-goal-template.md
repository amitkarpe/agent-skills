# Worker Goal Template

Goal:
- <one bounded objective>

Repo truth:
- <STATUS.md path>
- <PLANS.md path>

Do first:
- create or update local evidence under `~/.AGENTS-temp/<repo>/`
- read only the listed repo-truth files

Rules:
- keep scope bounded
- keep stable lanes untouched unless explicitly allowed
- use subagents internally only when read-heavy review or parallel checks help
- keep thread output short; store raw output in files

Success:
- <explicit success condition>

Stop if:
- <explicit blocker 1>
- <explicit blocker 2>

Evidence:
- `~/.AGENTS-temp/<repo>/<goal-or-run-name>/`

Report back:
- result
- blocker or success
- evidence path
- exact next step
