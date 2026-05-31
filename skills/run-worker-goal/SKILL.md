---
name: run-worker-goal
description: Execute an already prepared Codex worker goal. Use when Amit asks to run, continue, or refresh a worker lane such as td, tdg, tdm, pat, boss, or localai from a goal file. Defaults to direct/goal execution and uses plan-first only when explicitly requested or safety is unclear.
---

# Run Worker Goal

Use this skill when the worker goal is already prepared and Amit wants it
executed or continued.

Examples:

- `$run-worker-goal tdg`
- `give goal to TD`
- `run goal for TDM`
- `continue the worker goal`

## Core Rule

Do not run `/plan` by default.

The controller should already have done deep thinking with
`prepare-worker-goal`. This skill is for execution.

Choose the fastest safe mode:

1. `direct`: tiny bounded task or result/status packet; no `/plan`, no `/goal`.
2. `goal`: complete approved goal file; send `/goal` directly.
3. `plan-first`: broad/risky/unclear goal, or Amit explicitly asked for plan
   first.

## Default Truth Files

Use:

```text
AGENTS.md
CONTEXT.md
```

Do not recreate or rely on `PLANS.md` / `STATUS.md` unless the repo has an
explicit exception.

Goal files live under:

```text
~/.AGENTS-temp/<repo>/goals/
```

Results live under:

```text
~/.AGENTS-temp/<repo>/<run>/RESULT.md
~/.AGENTS-temp/work/inbox/<repo>.done
```

## Lane Mapping

- `td`, `trustdev`: repo `/home/dev/git/trustdev`, temp `/home/dev/.AGENTS-temp/trustdev`, tmux `trustdev`.
- `tdg`, `td-gitlab`, `trustdev-gitlab`: repo `/home/dev/git/trustdev-gitlab`, temp `/home/dev/.AGENTS-temp/trustdev-gitlab`, tmux `td-gitlab`.
- `tdm`, `td-mongodb`, `trustdev-mongodb`: repo `/home/dev/git/trustdev-mongodb`, temp `/home/dev/.AGENTS-temp/trustdev-mongodb`, tmux `td-mongodb`.
- `pat`, `patching`: repo `/home/dev/git/patching`, temp `/home/dev/.AGENTS-temp/patching`, tmux `patching`.
- `boss`: repo `/home/dev/git/boss`, temp `/home/dev/.AGENTS-temp/boss`, tmux `boss`.
- `localai`: repo `/home/dev/git/localai`, temp `/home/dev/.AGENTS-temp/localai-lab/repos/localai`, tmux `localai`.
- Generic fallback: repo `/home/dev/git/<lane>`, temp `/home/dev/.AGENTS-temp/<lane>`, tmux `<lane>`.

## Worker Model Gate

For office workers, prefer Spark xhigh execution:

```text
Run /status first and confirm model is gpt-5.3-codex-spark and reasoning is xhigh.
If not true, stop and ask controller to restart this worker with the correct model.
```

Controller restart shape:

```bash
codex resume --last --enable hooks -m gpt-5.3-codex-spark -c 'model_reasoning_effort="xhigh"'
```

Use stronger controller reasoning for planning and risk decisions; use Spark
xhigh workers for bounded execution.

## Mode Selection

### Direct

Use direct mode for narrow tasks:

- inspect a result packet
- update a done marker
- write a short closeout summary
- run local validation only
- no AWS mutation, no broad repo mutation

Prompt:

```text
Read and execute this bounded task file only: <absolute-goal-file>. Stop after writing the requested result packet.
```

### Goal

Use goal mode when the goal file is complete and approved.

Goal quality gate:

- one bounded mission
- outcome and verification surface
- allowed mutation and no-go boundaries
- read-first files
- Phase 0 Probe / MVP Proof / Full Lane only if / Closeout
- expected result packet and done marker
- blocked stop condition
- private-only guardrails for GCC/GovTech/AWS private lanes
- Inspector/CIS/HCR read-first rule when relevant

Prompt:

```text
/goal <lane> execution. Read <goal-file> first. Use AGENTS.md and CONTEXT.md as repo truth. Start with Phase 0 Probe, run MVP Proof next, enter Full Lane only if gates pass, then write Closeout. Stop on one clean result packet or a real blocker. Update the done marker.
```

### Plan-First

Use plan-first only when:

- Amit explicitly asked for plan first
- PROD mutation is new or broad
- IAM, VPC, networking, public exposure, rollback, or cleanup is unclear
- repo truth conflicts with live state
- required approval is ambiguous
- the goal may touch stable services
- the goal is missing any quality-gate field

Prompt:

```text
/plan Use <goal-file> as source of truth. Produce a bounded Probe -> MVP Proof -> Full Lane -> Closeout plan for <lane> only. Do not mutate AWS or repo files during plan mode. Ask only if a hard no-go boundary is unclear.
```

After `/plan`, implement only if:

- Amit asked to execute, not plan-only
- plan stays inside the goal boundaries
- no unresolved no-go question remains

If Codex asks `Implement this plan?`:

- choose `1. Yes, implement this plan` when context is below `30%`
- choose `2. Yes, clear context and implement` when context is `30%` or higher
- choose `3. No, stay in Plan mode` for unresolved or unapproved boundaries

## Workflow

1. Confirm target tmux session/window is Codex, not shell.
2. Read smallest useful truth:
   - repo `AGENTS.md`
   - repo or lane `CONTEXT.md`
   - goal file
   - latest done marker/result only if needed
3. Resolve truth conflicts before execution.
4. Select mode: `direct`, `goal`, or `plan-first`.
5. Submit only `@/absolute/path/to/goal.md` when possible.
6. Verify prompt is accepted and worker is `Working`.
7. Prefer hooks/done markers over live polling.

## Done Marker Contract

Ask workers to update:

```text
result: <done|blocked|next_ready|failed>
result_path: <absolute path>
safe_to_continue: <yes|no>
next_action: <one line>
blocked_reason: <empty or reason>
resource_ids: <AMI/instance/pipeline ids when relevant>
public_exposure: <none|null|details>
```

Controller can start the next loop without live polling only when
`safe_to_continue: yes` and the result packet proves the next action is inside
the current no-go gates.

## Completion Summary

Report:

- mode used
- goal path
- worker session/window
- result packet or expected result packet
- current status and next check
