---
name: worker-goal-preflight
description: Prepare a worker goal safely before sending it to another Codex lane. Use when Amit wants a short approval-first plan, a local goal file created or updated first, critical review with subagents where useful, and then a cleaned worker goal submitted without bloating the main context.
---

# Worker Goal Preflight

Use this skill when the task is not “do the work now,” but “prepare the best worker goal first.”

This skill is for controller-to-worker handoff quality.

## Core behavior

- Show Amit a short plan first.
- Keep the approval ask under 10 lines.
- Wait for approval before writing or sending the final worker goal.
- Create or update the local goal file first.
- Critically review and improve the goal before submission.
- For medium or large goals, prefer Codex internal task tracking so progress is
  visible as tasks/subtasks rather than only prose updates.
- Use subagents for read-heavy review, repo-truth checks, or parallel fact gathering when that reduces main-thread context.
- Keep the main thread focused on:
  - plan
  - decision
  - final worker goal
  - evidence paths

## When to use subagents

Use subagents when one or more of these are true:
- the repo truth is spread across multiple large files
- the worker goal depends on comparing repo state and live state
- you need an independent audit of the draft goal
- you want parallel review of:
  - repo truth
  - runtime state
  - risk or cleanup conditions

Do not overuse subagents for:
- tiny goals
- obvious one-step tasks
- heavily overlapping write work

## When to use internal task tracking

Prefer Codex internal plan/task tracking when one or more of these are true:
- the worker goal will likely run longer than a few minutes
- the goal has 3 or more distinct phases
- you want easy monitoring of completed vs pending work
- you expect mid-run feedback or correction from Amit

For tiny goals, skip it.

When used, the worker goal should explicitly ask the worker to:
- create a short internal task list first
- keep exactly one task in progress
- update task status as work moves
- surface blockers or failed tasks clearly

## Context threshold rule

Prefer explicit stop-or-restart discipline for medium or large worker lanes:
- around `70%` context:
  - switch harder to file-heavy, thread-light execution
- around `80%` context:
  - do not start a broad new lane
- around `85%` context:
  - finish only the current bounded goal, write compact summary/evidence, then stop
- around `90%` context:
  - treat the session as at compaction risk; restart before more work

When appropriate, the worker goal should explicitly say:
- stop at `80-85%` context after the current bounded task
- do not begin a new lane at high context
- prefer restart over unexpected compacting

## Workflow

1. Read only the minimum repo truth needed.
2. Draft a short plan for Amit in under 10 lines.
3. Wait for approval.
4. Create or update the local goal file first.
5. Review the draft goal critically.
6. Decide whether the worker should use internal task tracking.
7. Use subagents if they will reduce context or improve review quality.
8. Tighten the goal:
   - scope
   - stop condition
   - validation
   - evidence path
   - no-go boundaries
   - internal task tracking rule when appropriate
   - context threshold stop rule when the lane may run long
9. Submit the improved goal to the worker.
10. Report only the compact outcome.

## Goal quality checklist

Before sending the worker goal, confirm:
- the goal has one bounded objective
- repo truth files are named explicitly
- mutation limits are explicit
- stop conditions are explicit
- evidence path is explicit
- success criteria are explicit
- historical noise is excluded
- the worker is told when to use subagents internally
- the worker is told whether to use internal task tracking
- the worker is told when to stop for context threshold if the lane may run long

## Output contract

For Amit approval, use this shape:

```text
Plan:
1. ...
2. ...
3. ...

If approved, I will write the local goal file first, review it critically, then submit the improved goal to the worker.
```

Keep it under 10 lines.

After approval, final controller response should stay compact:

```text
Updated:
- <goal file path>

Submitted:
- <worker/session>

Goal:
- <2-5 line summary>
```

## Reusable goal template

Use [templates/worker-goal-template.md](templates/worker-goal-template.md) as the starting skeleton.
