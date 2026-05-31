# Worker Goal Template

Goal:
- <one bounded objective>

Repo truth:
- `AGENTS.md`
- `CONTEXT.md`

Goal file:
- `~/.AGENTS-temp/<repo>/goals/<YYYYMMDD-HHMM>-<short-goal>.md`

Do first:
- verify repo truth and live state only as needed
- create or update local evidence under `~/.AGENTS-temp/<repo>/`
- do not mutate AWS/repo files until approval and gates are clear

Rules:
- keep scope bounded
- keep stable lanes untouched unless explicitly allowed
- if the goal is medium or large, create and maintain a short internal task list
- use subagents internally only when read-heavy review or parallel checks help
- keep thread output short; store raw output in files
- if context reaches about `80-85%`, finish the current bounded task and stop
  before starting a new lane

Success:
- <explicit success condition>

Stop if:
- <explicit blocker 1>
- <explicit blocker 2>

Evidence:
- `~/.AGENTS-temp/<repo>/<goal-or-run-name>/RESULT.md`
- `~/.AGENTS-temp/work/inbox/<repo>.done`

Report back:
- result
- blocker or success
- evidence path
- exact next step
