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

## Workflow

1. Read only the minimum repo truth needed.
2. Draft a short plan for Amit in under 10 lines.
3. Wait for approval.
4. Create or update the local goal file first.
5. Review the draft goal critically.
6. Use subagents if they will reduce context or improve review quality.
7. Tighten the goal:
   - scope
   - stop condition
   - validation
   - evidence path
   - no-go boundaries
8. Submit the improved goal to the worker.
9. Report only the compact outcome.

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
