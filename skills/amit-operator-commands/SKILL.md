---
name: amit-operator-commands
description: Route Amit's heavier operator phrases into safe Codex workflows. Use for worker/status control such as "check td", "check cc", "check workers", "go td", "approved", "ss status", "did ss call?", "clear context", "debug tight", "fast work", "commit all", "push all", "merge", "cleanup", "TTL cleanup", and similar repo/AWS operator command shorthands. Do not trigger this skill only for simple global shortcuts like "next", "save context", or "save handoff" unless the repo lacks those global rules.
---

# Amit Operator Commands

Use this skill when Amit gives a short command phrase that implies a heavier
workflow rather than a single shell command.

Do not load this skill only to handle these global shortcuts when the active
instructions already define them:

- `next`
- `save context`
- `save handoff`
- `ask me`

Those should usually be handled from current repo truth with minimal context.
Use this skill when the shortcut expands into worker orchestration, cleanup,
git mutation, supervisor status, or a clean restart packet.

## Core rules

- Keep output short, practical, and current-state only.
- Prefer repo truth over chat memory: `AGENTS.md`, `CONTEXT.md`, optional
  `HANDOFF.md`, branch/MR/PR text, and current goal files when available.
- For old evidence or broad context questions, read `INDEX.md` / `MANIFEST.tsv`
  first when present, then use `qmd-agent-search` or targeted `rg` before raw
  evidence scans.
- Preserve local-only context. Do not stage secrets, `AGENTS.override.md`, raw evidence bundles, `.codex-local/`, or unrelated local files.
- Save durable task evidence under `~/.AGENTS-temp/<repo>/`.
- Before deleting or archiving context/rule files, create a backup under `~/back/`.
- For AWS cleanup, start read-only and load `~/.codex/AWS.md` before inventory or deletion.

## Shared context contract

- `AGENTS.md` = stable repo rules.
- `CONTEXT.md` = current truth and restart state.
- `HANDOFF.md` = explicit transfer snapshot only when Amit asks for handoff.
- Worker goal files = execution instructions, not repo truth.
- Worker `RESULT.md` files and `.done` markers = evidence and completion
  signals.
- `PLANS.md` and `STATUS.md` are retired unless the repo explicitly says
  otherwise.
- `/compact` should preserve this same model; it must not create `HANDOFF.md`
  or revive old plan/status files by itself.

## Command router

### Hot global shortcuts

These commands should stay cheap. If global `AGENTS.md` already defines them,
follow the global rule and avoid loading more old evidence than needed.

- `ask me`:
  - stop before implementation.
  - restate the request.
  - propose the smallest safe plan.
  - name files/systems to touch.
  - list no-go gates and validation.
  - ask one exact approval question.
  - wait for Amit's `go`.
- `next`, `next?`, `what next`:
  - inspect current repo truth and latest worker markers.
  - return one recommended next action plus up to two options.
  - do not run skills only to invent more work.
- `save context`:
  - update only `CONTEXT.md`.
  - do not create `HANDOFF.md` or dated snapshots.
- `save handoff`:
  - update `CONTEXT.md` and `HANDOFF.md`.
  - keep it compact and decision-grade.

### Short worker commands

Use this section before the broader command handlers when Amit gives a short
worker phrase.

Source order for worker decisions:

1. Current repo `CONTEXT.md`
2. Latest `~/.AGENTS-temp/work/inbox/<repo>.done`
3. Latest worker `RESULT.md`
4. Active tmux pane only to confirm live state or stale markers
5. Prepared goal files under `~/.AGENTS-temp/<repo>/goals/`
6. Branch/MR/issue state when repo work is involved
7. `HANDOFF.md` only for restart/resume or stale `CONTEXT.md`

Do not use broad chat history as the source of truth.

Alias routing:

- `check <lane>`, `status <lane>`, `<lane>?`, `update <lane>`:
  status-only check; no edits, no new goals, no AWS mutation.
- `check cc`, `check aa`, `check td`, `check pat`,
  `check workers`, `are all workers active?`:
  status-only check; inspect markers/results first, then tmux only to confirm
  stale or live state.
- `ss status`, `did ss call?`, `is ss working?`:
  inspect supervisor last-run files and latest summary before assuming a wake
  failure. Report timestamp, decision, target state, and whether a wake was
  expected.
- `next?`, `next`, `what next`:
  inspect current truth and recommend one next action plus up to two options.
- `prep <lane>`, `prepare <lane>`, `goal <lane>`,
  `$prepare-worker-goal <lane>`:
  use `prepare-worker-goal`; write or refresh a goal, do not run it.
- `go <lane>`, `run <lane>`, `continue <lane>`, `give goal <lane>`,
  `$run-worker-goal <lane>`:
  use `run-worker-goal`; run only an approved prepared goal.
- `approved`:
  run only when the target prepared goal is unambiguous. If multiple current
  goals or lanes are plausible, stop and ask for the lane/path.
- `approved for all`, `take any approval from me`, `approved - upgrade SPEC`:
  treat as approval only inside already-known specs/goals. Do not invent new
  mutation scope. If multiple prepared goals are plausible, ask for the target
  lane or goal path.
- `approve and run <lane>`:
  run only when the approval target, no-go gates, and prepared goal are clear.

Preferred output shape for these short commands:

- `State`
- `Recommended`
- `Needs approval`
- `Next command`

Worker-state routing:

- If worker is `Working`, do not prepare or submit another goal unless Amit
  explicitly asks for side work. Report current result path and next check.
- If latest marker is `blocked`, summarize the blocker and recommend either
  `prepare-worker-goal` or the exact approval/Ops ask needed.
- If latest marker is `done` and `safe_to_continue=yes`, use `next_action` to
  recommend the next goal or wait state.
- If marker/result is stale, inspect tmux once and say it is stale.
- If there is no active worker and no prepared goal, recommend
  `prepare-worker-goal`.

Examples:

- `check td` -> status-only TD marker/result/tmux check.
- `next?` -> one recommended next action and up to two options.
- `prep td` -> prepare a TD goal, do not run.
- `go td` -> run an approved TD goal only if unambiguous.
- `approved` -> run the latest prepared goal only if exactly one target is
  clear.

### `clear context`

Goal: prepare a genuinely clean restart packet so the next session can reload a
small file set instead of inheriting a large compacted chat.

Use when Amit says:

- `clear context`
- `clean start`
- `reset context`
- `start team context`

Rules:

- Refresh `CONTEXT.md` and `HANDOFF.md` when those files exist in the repo.
- Write one compact reset packet under `~/.AGENTS-temp/<repo>/`.
- Include only:
  - read-first order
  - current truth
  - active workers and marker paths
  - blockers and approvals already granted
  - next safe command
  - what not to reload
- Do not create many dated snapshots.
- Do not bulk-copy chat history.
- Stop after writing the packet and tell Amit to start the clean session from
  that packet.
- Be explicit that the current session context cannot be reduced in-place; the
  packet is for a fresh session.

Output:
- `Updated`
- `Reset packet`
- `Read first`
- `Next`

### `dump_context_fast`

Goal: update only `CONTEXT.md` from current state.

Use when Amit says:

- `dump_context_fast`
- `dump_context_fast: ...`

Rules:

- Do not create dated `CLEAN_*`, `HANDOFF_*`, or extra `CONTEXT_*` files.
- Do not load compact prompts, old handoff files, GOAL files, result packets,
  or broad history unless required to identify the active blocker.
- Use current status commands, active tmux panes, git status, and latest result
  filenames only.
- Update the repo or lane `CONTEXT.md`.
- Preserve only current truth, blocker, next action, read-first order, and
  latest evidence paths.
- Stop after updating.

Output:
- `Updated`
- `Latest evidence`
- `Next`

### `save handoff`

Goal: create or refresh `HANDOFF.md` for a session/milestone boundary.

Use when Amit says:

- `save handoff`
- `clean start handoff`
- `session handoff`

Rules:

- This updates `CONTEXT.md` and `HANDOFF.md`.
- Keep it decision-grade: current truth, active blockers, read-first order,
  latest evidence paths, decisions, no-go gates, and lessons that affect future
  execution.
- Do not bulk-copy old chat history.
- Back up existing `HANDOFF.md` before major replacement.
- Do not create `PLANS.md`, `STATUS.md`, or dated handoff files unless Amit
  explicitly asks.

Output:
- `Updated`
- `Read first`
- `Next`

### `save context`

Goal: update `CONTEXT.md`.

Rule:

- Update `CONTEXT.md` with current truth, blocker, next action, evidence paths,
  read-first order, and active no-go gates.
- Do not create `HANDOFF.md` unless Amit says `save handoff`.
- Do not create `PLANS.md`, `STATUS.md`, dated context snapshots, or compact
  resume files.

Output:
- `Updated`
- `Next`

### `what next` / `next`

Goal: choose the next useful task or goal.

Workflow:
1. Read the smallest relevant repo context:
   - `INDEX.md` / `MANIFEST.tsv` first when present and the question touches
     old evidence, cleanup, or lane history
   - `CONTEXT.md`, guidance files, git status, and active
     PR/MR/issue if present
2. Use `qmd-agent-search "<query>"` for old summarized evidence when available;
   use targeted `rg` for exact IDs or strings.
3. Check `/goal` when runtime exposes it, but do not treat it as source of truth.
4. Return a short shortlist of 1-3 next actions, with one recommended default.
5. Do not edit files unless Amit also asks to implement.

Output:
- `State`
- `Recommended`
- `Options`

### `debug tight`

Goal: understand and fix the smallest real failure.

Workflow:
1. Reproduce or confirm the smallest failure.
2. Inspect only relevant files/logs.
3. Make the smallest safe fix.
4. Run the narrowest useful validation.
5. Stop before refactors or cleanup detours.

Output:
- `Problem`
- `Cause`
- `Fix`
- `Validated`
- `Next`

### `fast work`

Goal: complete a small private-repo task at MVP quality.

Workflow:
1. Inspect only relevant files.
2. Implement the smallest useful change.
3. Run small validation.
4. Update `CONTEXT.md` only if task state changed.
5. Commit only when the repo changed and the change is coherent.

Output:
- `Changed`
- `Validated`
- `Git`
- `Next`

### `commit all`

Goal: make one accurate local commit.

Workflow:
1. Inspect `git status --short`, unstaged diff, staged diff, ignored/local-only rules, and recent commits.
2. Exclude secrets, raw evidence, unrelated local-only files, and user edits outside the requested scope.
3. Run the smallest relevant validation; use `bash -n` for shell changes.
4. Stage intended files only.
5. Commit with a specific message that matches the actual diff.
6. Do not push.

Output:
- `Committed`
- `Validation`
- `Not staged`
- `Next`

### `push all`

Goal: publish the current branch safely.

Workflow:
1. If dirty, run the `commit all` workflow first.
2. Confirm current branch and upstream.
3. Push the current branch.
4. Report PR/MR URL or remote branch if discoverable.
5. Do not merge.

Output:
- `Pushed`
- `Branch`
- `Remote`
- `Next`

### `merge`

Goal: finish the PR/MR path.

Workflow:
1. Run `commit all` and `push all` behavior as needed.
2. Discover the active PR/MR from branch metadata, `gh`, `glab`, or repo remotes.
3. Update the PR/MR/issue summary with what changed, validation, and any residual risk.
4. Verify required checks when tooling exposes them.
5. Merge only when target, checks, and merge method are unambiguous.
6. After merge, close linked issue only when the PR/MR or user request clearly indicates it.
7. Clean up local branch only after confirming merge success.

Stop if:
- multiple PRs/MRs match
- checks are failing or unknown and required
- merge target is ambiguous
- deletion would remove user work

### `cleanup`

Goal: remove unwanted local task debris without losing useful history.

Workflow:
1. Read current task/plan/goal and git status.
2. Read `INDEX.md` / `MANIFEST.tsv` first when present.
3. Inventory candidate generated files: temp scripts, raw JSON/log dumps, one-off reports, stale compact files, caches, and local scratch.
4. Keep curated docs, final reports, tracked status files, repo truth, closeout
   packets, decision packets, cleanup proof, MR/Jira references, and scan summaries.
5. Archive/compress raw evidence before deletion when retention is unclear.
6. Back up before deleting anything that might contain context.
7. Do not delete tracked files unless Amit explicitly asked for that tracked-file cleanup.
8. Delete evidence only after closeout exists, no active lane references it, and
   Amit approved deletion or a clear `delete_after` rule applies.

Output:
- `Removed`
- `Backed up`
- `Kept`
- `Needs decision`

### `TTL cleanup`

Goal: clean up expired or unwanted temporary AWS resources.

Workflow:
1. Load `~/.codex/AWS.md`.
2. Start read-only: inventory resources with TTL/cleanup tags and repo resource records.
3. Save inventory/evidence under `~/.AGENTS-temp/<repo>/`.
4. Treat expired `ttl` + `cleanup=delete` resources as candidates, not automatic deletion, unless Amit explicitly asked to delete them.
5. Before deleting, report resource type, ID, name, region/account/profile, TTL, cleanup tag, and planned command.
6. Delete only resources matching the approved candidate set.
7. Verify deletion and save final evidence.

Output:
- `Candidates`
- `Deleted`
- `Verified`
- `Kept`
- `Needs decision`
