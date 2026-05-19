---
name: go-plan-run-goal
description: Use when Amit asks to refresh or start a Codex worker lane with a plan-first, probe-gated GOAL workflow. Accepts an explicit lane name or infers the active lane, writes lane-local GOAL.md by default, sends /plan first, then /goal when approved, with a normal prompt fallback for long-running execution loops.
---

# Go Plan Run Goal

Use this skill when Amit says things like:

- `$go-plan-run-goal td-mongodb`
- `go plan run goal for tdg and tdm`
- `refresh GOAL.md and start the lane`
- `use plan mode then /goal`
- `start active lane from GOAL.md`
- `probe first then run the lane`

## Core Rule

Default lane shape:

1. `Phase 0 Probe`
2. `MVP Proof`
3. `Full Lane` only if proof and approval gates pass
4. `Closeout`

Medium/large lanes must start with `Phase 0 Probe` unless fresh evidence
already proves the lane shape or Amit explicitly overrides it.

Prefer lane-local truth under the temp directory. Do not dirty an MR-ready repo
branch just to start or refresh a worker lane.

Use Goals as compact completion contracts. Every generated worker goal should
state the outcome, verification surface, constraints, boundaries, iteration
policy, and blocked stop condition.

Explicit `$go-plan-run-goal <lane>` means Amit approved the normal
plan-then-run flow for that lane. After `/plan` returns, continue into bounded
implementation unless Amit explicitly says `plan only`, the plan contains
unresolved questions, or the plan would cross a no-go boundary not already
approved in the lane-local `GOAL.md`.

This pre-approval does not override hard safety gates. Stop before public
exposure, AWS mutation outside the goal, PROD mutation outside the goal,
repo-tracked edits outside the goal, ambiguous rollback/cleanup, or any
Inspector/CIS invalid-result condition.

## Inputs

- Lane may be explicit: `tdg`, `tdm`, `td-gitlab`, `td-mongodb`, `trustdev-gitlab`, `trustdev-mongodb`.
- If no lane is explicit, infer from cwd, tmux session/window, or nearest local `GOAL.md`.
- If more than one active lane is plausible, ask one short clarification unless Amit clearly said all or named multiple lanes.
- If Amit asks to improve this skill or run skill cycles, use temp-only mode
  unless Amit explicitly approves real repo or AWS mutation.

## Lane Mapping

- `tdg`, `td-gitlab`, `trustdev-gitlab`: repo `/home/dev/git/trustdev-gitlab`, temp `/home/dev/.AGENTS-temp/trustdev-gitlab`, tmux `td-gitlab`.
- `tdm`, `td-mongodb`, `trustdev-mongodb`: repo `/home/dev/git/trustdev-mongodb`, temp `/home/dev/.AGENTS-temp/trustdev-mongodb`, tmux `td-mongodb`.
- Generic fallback: repo `/home/dev/git/<lane>`, temp `/home/dev/.AGENTS-temp/<lane>`, tmux `<lane>`.

## Workflow

1. Inspect the target before sending anything:
   - `tmux list-windows -t <session>`
   - `tmux capture-pane -t <session>:codex -p -S -60`
   - if no `codex` window exists, inspect likely windows before deciding.
   - treat the pane as safe only when no unrelated or risky worker execution
     is active; an approved Probe/MVP/Full skill-test running in that pane is
     not a blocker by itself.
2. Read the smallest useful truth set:
   - lane temp or repo temp `INDEX.md` and `MANIFEST.tsv` if present,
     especially for `next`, cleanup, closeout, or old-evidence questions
   - lane temp `STATUS.md`, `PLANS.md`, `COMPACT_RESUME_CURRENT.md` if present
   - lane temp `GOAL.md` if present; when this is the current controller goal,
     prefer it over stale older status text that points to repo `GOAL.md`
   - lane temp files named like `<LANE>_NEXT_GOAL_CURRENT.md` if present;
     treat them as current-goal candidates, not merely old evidence
   - legacy lane temp `CURRENT_WORKER_GOAL.md` if present; use it as input,
     but prefer creating or refreshing lane temp `GOAL.md` for the next run
   - repo `GOAL.md`, `STATUS.md`, or `PLANS.md` only when needed for current truth
   - for any Inspector/CIS/HCR/AMI compliance scan work, also read `~/.codex/AWS_INSPECTOR_CIS.md`.
   - if QMD is installed and the question concerns old summarized evidence,
     use `qmd-agent-search "<query>"` before broad-scanning raw evidence folders.
3. Resolve truth conflicts before starting execution:
   - compare current mission, active AMI/resource ids, allowed mutation, and
     stop boundary across temp `GOAL.md`, temp next-goal files, temp
     `STATUS.md`/`PLANS.md`, and repo `GOAL.md` when read
   - if they disagree on the active mission or safe next step, run only
     `Phase 0 Probe`; write the conflict and recommended source of truth into
     lane-local `<temp>/GOAL.md` or a dated probe note, then stop before
     `/goal`
   - do not let a newer temp next-goal file silently override a repo `GOAL.md`
     unless the generated goal states that choice and why
4. Create or update lane-local `<temp>/GOAL.md` before starting or restarting
   work. Update repo `GOAL.md` only when that repo already uses it for active
   lane truth and it is not MR-ready, or Amit explicitly asks. Include:
   - lane mission and stop boundary
   - read-first truth files
   - files the worker must not edit
   - current state, blocker, and next result packet expected
   - `Phase 0 Probe`, `MVP Proof`, `Full Lane only if`, and `Closeout` sections
   - goal contract fields: outcome, verification surface, constraints,
     boundaries, iteration policy, and blocked stop condition
   - evidence index behavior: which `INDEX.md` / `MANIFEST.tsv` files to read
     or update, and what raw evidence folders must not be scanned unless needed
   - private-only AWS guardrail when the lane touches AWS
   - forced `~/.codex/AWS_INSPECTOR_CIS.md` read-first entry when the lane has an Inspector/CIS gate
   - plan-first startup and fallback execution prompt.
5. Do not interrupt active risky execution. If the pane is already working on the lane, update `GOAL.md` if needed and report current status instead of sending a new prompt.
6. Send `/plan` first for medium or large lane work. Plan mode may ask questions; allow that when useful.
7. After the plan returns, treat explicit `$go-plan-run-goal <lane>` as Amit's
   approval to continue into bounded execution unless he said `plan only` or
   the plan has unresolved questions/no-go violations. Try `/goal` once if
   supported. If `/goal` fails, sends nothing, or is not available, use the
   fallback prompt.
8. Verify after every send:
   - capture the pane again.
   - if the prompt is still sitting in input, send one extra `Enter`.
   - if Codex shows a plan modal, send one `Enter` and recapture.
   - if Codex asks `Implement this plan?`, choose the implementation option
     when the current user command is explicit `$go-plan-run-goal <lane>` and
     the plan stays inside the lane-local `GOAL.md` no-go gates:
     - choose `1. Yes, implement this plan` when context is below `30%`
     - choose `2. Yes, clear context and implement` when context is `30%` or
       higher
     - choose `3. No, stay in Plan mode` only when Amit said `plan only`, the
       plan asks unresolved questions, or the plan would cross an unapproved
       no-go boundary
     - after choosing, recapture the pane
   - if `/goal` is accepted but the pane remains `Ready` with `Pursuing goal`,
     send one short kickoff prompt such as `Continue the active goal now`,
     then recapture.
   - if the window is at shell, do not paste the worker prompt into shell; restart or resume Codex first.

## Temp-Only Skill Cycle Mode

Use this mode when Amit asks to improve `go-plan-run-goal`, run a few cycles,
or test a lane workflow without approving real execution.

- Allowed mutation:
  - lane-local temp files under `<temp>`
  - autoresearch notes under `~/.AGENTS-temp/agent-skills/autoresearch/go-plan-run-goal/`
- Not allowed:
  - AWS mutation
  - repo-tracked edits in the target execution repo
  - merge, push, Image Builder, EC2 launch, Inspector scan, DNS, LB, or rollout
- Cycle shape:
  1. `Probe`: inspect pane and truth files, then record conflicts and no-go
     boundaries.
  2. `MVP`: create a lane-local goal that would be safe to hand to a worker.
  3. `Temp-only Full`: exercise the full prompt/goal shape but stop at a
     lane-local closeout packet.
- If temp-only mode finds a real execution path, report it as a next safe step;
  do not perform it in the same cycle.

## Evidence Index and Cleanup Behavior

Use this section when Amit asks `next`, `cleanup`, `closeout`, or asks about old
evidence.

- Read first:
  - `<temp>/INDEX.md` if present
  - `<temp>/MANIFEST.tsv` if present
  - `<temp>/STATUS.md`, `<temp>/PLANS.md`, `<temp>/GOAL.md`
  - latest `*CLOSEOUT*.md`, `*PACKET*.md`, `*DECISION*.md`, or `*SUMMARY*.md`
    only when needed
- Search:
  - use `qmd-agent-search "<query>"` for old summarized evidence when available
  - use targeted `rg` for exact IDs, paths, AMIs, instances, issues, or strings
  - avoid broad `find`/raw folder scans unless index/search points there
- Closeout:
  - write a short closeout packet with result, evidence path, blocker/success,
    next safe step, cleanup needed, and retention/delete-after hints
  - update `INDEX.md` or `MANIFEST.tsv` when the lane created durable evidence
    or cleanup candidates
- Cleanup:
  - cleanup temporary cloud resources while context is fresh
  - preserve final closeout packets, decision packets, cleanup proof, MR/Jira
    references, and scan summaries
  - archive or compress raw logs, large JSON, and repeated failed-run folders
  - delete evidence only after closeout exists, no active lane references it,
    cleanup proof is saved when relevant, and Amit approved deletion or a clear
    `delete_after` rule applies

## Prompt Templates

Plan:

```text
/plan Use <temp>/GOAL.md as the source of truth. Read lane-local truth files under <temp> first, then repo truth only if needed. Produce a bounded Probe -> MVP Proof -> Full Lane -> Closeout plan for <lane> only. The goal contract must include outcome, verification surface, constraints, boundaries, iteration policy, and blocked stop condition. Ask clarifying questions only if needed. Do not mutate AWS or files during plan mode.
```

Goal:

```text
/goal <lane> long-running loop. Read <temp>/GOAL.md first. Use only lane-local truth under <temp> unless the goal names repo files. Work only from <repo>. Keep private-only guardrails. Start with Phase 0 Probe, run MVP Proof next, enter Full Lane only if the goal gates pass, then write a Closeout packet. Preserve the goal contract: outcome, verification surface, constraints, boundaries, iteration policy, and blocked stop condition. Stop on one clean result packet or a real blocker. Update lane-local truth files as you go.
```

Fallback:

```text
Read <temp>/GOAL.md first, then execute the lane from that file. Use only lane-local truth under <temp> unless the goal names repo files. Work only from <repo>. Keep private-only guardrails. Start with Phase 0 Probe, run MVP Proof next, enter Full Lane only if the goal gates pass, then write a Closeout packet. Preserve the goal contract: outcome, verification surface, constraints, boundaries, iteration policy, and blocked stop condition. Stop on one clean result packet or a real blocker. Update lane-local truth files as you go.
```

## Lane-Local GOAL.md Shape

```text
# <lane> GOAL

Mission:
- <one bounded objective>

Goal contract:
- outcome: <what must be true at completion>
- verification surface: <artifact, command, evidence, or report that proves it>
- constraints: <things that must not regress>
- boundaries: <repos, files, accounts, tools, hosts, and resources allowed>
- iteration policy: <how to choose next attempt after evidence>
- blocked stop condition: <when to stop and what to report>

Read first:
- <temp>/INDEX.md if present
- <temp>/MANIFEST.tsv if present
- <temp>/GOAL.md
- <temp>/STATUS.md if present
- <temp>/PLANS.md if present
- <repo truth files only when needed>

Phase 0 Probe:
- verify repo truth, live pane state, approvals, blockers, and no-go boundaries
- do not mutate AWS or repo files during probe unless Amit explicitly approved

MVP Proof:
- run the smallest proof that validates the lane direction

Full Lane only if:
- MVP proof passes
- approval exists
- rollback/cleanup and stop gates are clear

Allowed mutation:
- <read-only / one file / one host / one document / one validation target>

Stop immediately if:
- approval is missing
- stable services would be touched
- private-only guardrail would be violated
- repo truth and live state disagree
- rollback or cleanup is unclear

Closeout packet:
- result
- blocker or success
- evidence path
- next safe step
- cleanup needed
- retention/delete-after hints
- INDEX.md or MANIFEST.tsv update needed
```

## Truth Conflict Probe Note Shape

```text
# <lane> Goal Probe

Result:
- blocked_before_execution | clean_to_plan | clean_to_goal

Truth sources checked:
- <temp>/GOAL.md
- <temp>/<LANE>_NEXT_GOAL_CURRENT.md
- <temp>/STATUS.md
- <temp>/PLANS.md
- <repo>/GOAL.md if read

Conflict:
- <mission/source A>
- <mission/source B>

Decision:
- active source of truth: <path or none yet>
- reason: <freshness/evidence/explicit Amit instruction>

No-go:
- <AWS/repo/service mutation not approved>

Next safe step:
- <write goal / ask Amit / run plan / stop>
```

## Output

Keep the final answer short:

- `Updated`: `GOAL.md` path and any lane truth files touched.
- `Started`: lane, tmux session/window, and method used: `/plan`, `/goal`, or fallback prompt.
- `Status`: current pane state and next check.
