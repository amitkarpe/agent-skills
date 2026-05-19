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

## Inputs

- Lane may be explicit: `tdg`, `tdm`, `td-gitlab`, `td-mongodb`, `trustdev-gitlab`, `trustdev-mongodb`.
- If no lane is explicit, infer from cwd, tmux session/window, or nearest local `GOAL.md`.
- If more than one active lane is plausible, ask one short clarification unless Amit clearly said all or named multiple lanes.

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
   - lane temp `STATUS.md`, `PLANS.md`, `COMPACT_RESUME_CURRENT.md` if present
   - lane temp `GOAL.md` if present; when this is the current controller goal,
     prefer it over stale older status text that points to repo `GOAL.md`
   - legacy lane temp `CURRENT_WORKER_GOAL.md` if present; use it as input,
     but prefer creating or refreshing lane temp `GOAL.md` for the next run
   - repo `GOAL.md`, `STATUS.md`, or `PLANS.md` only when needed for current truth
   - for any Inspector/CIS/HCR/AMI compliance scan work, also read `~/.codex/AWS_INSPECTOR_CIS.md`.
3. Create or update lane-local `<temp>/GOAL.md` before starting or restarting
   work. Update repo `GOAL.md` only when that repo already uses it for active
   lane truth and it is not MR-ready, or Amit explicitly asks. Include:
   - lane mission and stop boundary
   - read-first truth files
   - files the worker must not edit
   - current state, blocker, and next result packet expected
   - `Phase 0 Probe`, `MVP Proof`, `Full Lane only if`, and `Closeout` sections
   - private-only AWS guardrail when the lane touches AWS
   - forced `~/.codex/AWS_INSPECTOR_CIS.md` read-first entry when the lane has an Inspector/CIS gate
   - plan-first startup and fallback execution prompt.
4. Do not interrupt active risky execution. If the pane is already working on the lane, update `GOAL.md` if needed and report current status instead of sending a new prompt.
5. Send `/plan` first for medium or large lane work. Plan mode may ask questions; allow that when useful.
6. After the plan is accepted or Amit says go, try `/goal` once if supported. If `/goal` fails, sends nothing, or is not available, use the fallback prompt.
7. Verify after every send:
   - capture the pane again.
   - if the prompt is still sitting in input, send one extra `Enter`.
   - if Codex shows a plan modal, send one `Enter` and recapture.
   - if Codex asks `Implement this plan?`, do not choose yes unless Amit
     explicitly approved Full Lane execution; dismiss it or choose the
     stay-in-plan/no option, then recapture.
   - if `/goal` is accepted but the pane remains `Ready` with `Pursuing goal`,
     send one short kickoff prompt such as `Continue the active goal now`,
     then recapture.
   - if the window is at shell, do not paste the worker prompt into shell; restart or resume Codex first.

## Prompt Templates

Plan:

```text
/plan Use <temp>/GOAL.md as the source of truth. Read lane-local truth files under <temp> first, then repo truth only if needed. Produce a bounded Probe -> MVP Proof -> Full Lane -> Closeout plan for <lane> only. Ask clarifying questions only if needed. Do not mutate AWS or files during plan mode.
```

Goal:

```text
/goal <lane> long-running loop. Read <temp>/GOAL.md first. Use only lane-local truth under <temp> unless the goal names repo files. Work only from <repo>. Keep private-only guardrails. Start with Phase 0 Probe, run MVP Proof next, enter Full Lane only if the goal gates pass, then write a Closeout packet. Stop on one clean result packet or a real blocker. Update lane-local truth files as you go.
```

Fallback:

```text
Read <temp>/GOAL.md first, then execute the lane from that file. Use only lane-local truth under <temp> unless the goal names repo files. Work only from <repo>. Keep private-only guardrails. Start with Phase 0 Probe, run MVP Proof next, enter Full Lane only if the goal gates pass, then write a Closeout packet. Stop on one clean result packet or a real blocker. Update lane-local truth files as you go.
```

## Lane-Local GOAL.md Shape

```text
# <lane> GOAL

Mission:
- <one bounded objective>

Read first:
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
```

## Output

Keep the final answer short:

- `Updated`: `GOAL.md` path and any lane truth files touched.
- `Started`: lane, tmux session/window, and method used: `/plan`, `/goal`, or fallback prompt.
- `Status`: current pane state and next check.
