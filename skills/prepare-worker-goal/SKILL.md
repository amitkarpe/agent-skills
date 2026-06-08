---
name: prepare-worker-goal
description: Prepare a high-quality worker goal before execution. Use when Amit wants the controller to think, review risk, inspect current repo/live truth, write or refresh a worker goal file, and optionally ask approval before handing it to a worker.
---

# Prepare Worker Goal

Use this skill when the task is not “execute now,” but “prepare the best worker
goal first.”

This is the controller thinking skill.

## Core Behavior

- Think before delegation.
- Read only the minimum repo/live truth needed.
- Write a clear goal file under `~/.AGENTS-temp/<repo>/goals/`.
- Review the goal critically before it is sent.
- Ask Amit for approval when the next step mutates AWS, stable services, IAM,
  networking, or production-like state.
- Do not execute the worker unless Amit explicitly asks to run it.
- Do not prepare a child/next goal while the target worker is still `Working`,
  unless Amit explicitly asks for sidecar preparation. If the current worker
  result is missing, check status and wait.

## Default Truth Files

Use:

```text
AGENTS.md
CONTEXT.md
```

Avoid `PLANS.md`, `STATUS.md`, and repo-root `GOAL.md` unless the repo has an
explicit exception.

## When To Use Subagents

Use subagents when one or more are true:

- repo truth is spread across multiple large files
- live state and repo state must be compared
- goal needs independent risk/audit review
- multiple facts can be gathered safely in parallel

Do not use subagents for tiny linear tasks.

## Goal Quality Checklist

Before sending a worker goal, confirm:

- one bounded objective
- explicit repo and lane
- explicit read-first files
- allowed mutation
- no-go boundaries
- stop conditions
- success criteria
- evidence path
- done marker path
- cleanup/rollback expectation
- worker model/session expectation when relevant
- whether the worker should use internal subagents
- context threshold stop rule for long lanes

## Worker Status Gate

Before writing or refreshing a worker goal:

1. Read `CONTEXT.md`.
2. Read the latest `~/.AGENTS-temp/work/inbox/<repo>.done` marker if present.
3. Read the referenced `RESULT.md` only when the marker exists or the context
   points to it.
4. Inspect tmux only if the marker/result is stale or the worker may still be
   running.

Rules:

- Worker `Working`: do not prepare a child goal. You may prepare a sidecar doc
  or checklist only if Amit explicitly asked for work that can run while
  waiting.
- Marker `blocked`: prepare a follow-up goal only after the blocker is
  understood and the needed approval/Ops ask is explicit.
- Marker `done safe_to_continue=yes`: prepare the next goal from `next_action`
  if it stays inside no-go gates.
- Multiple possible goals: stop and ask for lane/path instead of guessing.
- AWS mutation goal: include the exact approval sentence needed in the output.

## Goal File Shape

```text
# <lane> goal - <short name>

Controller timestamp:
Worker:
Repo:
Temp root:

Objective:
- <one bounded objective>

Read first:
1. AGENTS.md
2. CONTEXT.md
3. <this goal file>

Allowed mutation:
- <read-only / exact files / one host / one AWS action>

No-go boundaries:
- <what must not be touched>

Phase 0 Probe:
- <checks before mutation>

MVP Proof:
- <smallest proof>

Full Lane only if:
- <gates>

Stop immediately if:
- <blockers>

Success condition:
- <what proves done>

Closeout:
- write RESULT.md
- update done marker
- include next safe action and cleanup
```

## Output Contract

For Amit approval, use:

```text
State:
- ...

Recommended:
- ...

Needs approval:
- yes/no, and why

Next command:
- ...
```

After preparing:

```text
Prepared:
- <goal file path>

Worker:
- <session/repo>

Needs approval:
- <yes/no and why>

Next command:
- <for example: $run-worker-goal td>
```
