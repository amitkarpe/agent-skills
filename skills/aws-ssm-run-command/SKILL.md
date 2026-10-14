---
name: aws-ssm-run-command
description: Use this skill when users ask to run AWS Systems Manager Run Command (send-command/get-command-invocation), wait for terminal status, and collect stdout/stderr evidence with a reliable wrapper flow.
---

# AWS SSM Run Command

## Overview

Use this skill for reliable AWS SSM Run Command operations with a fixed contract:
- send command payload safely
- wait with transient readback retry handling (never resend the mutation)
- return triage evidence (`CommandId`, `Status`, `ResponseCode`, `StdOut`, `StdErr`)

## When To Use

Use this skill when user intent includes:
- `send-command`
- `AWS-RunShellScript`
- `get-command-invocation`
- waiting for command completion
- collecting run evidence for audit or triage

Do not use this skill for:
- State Manager associations
- Automation document workflows
- Patch Manager orchestration

## Inputs Required

- `region`
- target instance id(s)
- command text file
- run comment
- optional AWS profile (if ambient creds are not used)

## Workflow

1. Before a new or repeated send, check the owning run's durable CommandId and
   provider state. If a prior ID exists, read back that exact execution; do not
   send again. Running means wait; terminal means report its result. An unknown
   send outcome means stop and reconcile with SSM, not retry.
2. Build a command file with bash-safe commands. For a durable run, prefer
   `ssm_run.sh --command-id-file <run>/command-id.txt`; it requires and reserves a pending
   marker before sending and resumes readback from a recorded ID.
3. Use `ssm_wait.sh` and `ssm_get_output.sh` for exact-ID readback. Their
   transient API retries do not repeat `send-command`.

This is a mutation guard, not extra ceremony for read-only AWS calls. The
owning repository still supplies approval and any required account/role/region
identity gate. A terminal failure alone does not authorize a new send.

## Pre-send command and evidence checks

- Validate the **actual rendered** `AWS-RunShellScript` commands array, not only
  the source Bash file. Confirm line joining, quoting, selected interpreter,
  helper/prologue order and required environment. For a changed boundary, run
  the final assembled command with harmless fixture values and mocked AWS
  calls; `bash -n` alone is not an execution check. Never send a provider
  command merely to validate rendering.
- Treat `HOME` as optional in non-login SSM shells. Resolve effective-user
  home metadata explicitly when needed, using a task-specific variable instead
  of overwriting `HOME` or modifying authentication/configuration.
- Before dependent steps (for example, a restore), require the application's
  **supported initialization-complete signal** with a bounded wait. A port
  opening, `SELECT 1` or container-running state alone is not proof that a
  concurrent initializer finished. Fail closed on timeout or initializer exit.
- For a terminal failure, retain the **first failing operation**, response
  code and a small sanitized failure category/context in the initial report;
  keep raw stdout/stderr private when they may contain credentials or data.
  Generic `Failed/1` or `exit status 14` without causal context should
  prompt one bounded inspection, not repeated broad diagnostics.
- Bound diagnostic input, runtime and output. Verify any memory cap against
  the actual interpreter footprint; a restrictive virtual-address limit can
  produce `MemoryError` in the classifier itself, not the target workload.
- Report separately: local/rendered-code check, exact SSM terminal result,
  workload outcome and milestone acceptance. A terminal `Success/0` is not
  automatically application readiness or accepted migration evidence.
  Preserve one-send/exact-CommandId reconciliation; an UNKNOWN submission
  never authorizes another send.

## Script Usage

- `scripts/ssm_send.sh`: send command and print `CommandId`
- `scripts/ssm_wait.sh`: wait loop with transient retry window
- `scripts/ssm_get_output.sh`: fetch final invocation output
- `scripts/ssm_run.sh`: orchestration wrapper returning normalized JSON

## MCP route (`aws_sigv4` `run_script` in Codex)

Use this when the thread sends SSM commands through `aws_sigv4` instead of the
wrapper scripts. Same contract: one send, exact-ID readback, no resend on an
unknown outcome. Evidence for the rules below: work#183 (gg sent 87 commands
and made 494 `GetCommandInvocation` calls, 477 of them one model turn per poll).

- **Send:** one `SendCommand` per approved run, with a unique `Comment`. Put
  the identity assert in the same script. Return only `CommandId`, `Status`
  and `Comment`, and record the `CommandId` before waiting. The proxy timeout
  is 60 s: if the send call fails or times out, reconcile with
  `ListCommands` filtered by that `Comment` before any new send.
- **Wait inside one exec**, never one model turn per poll. Print only the
  terminal fields; return output tails, not full output.
- Keep each `run_script` short (one readback per call); do the waiting in the
  exec loop, not inside the sandbox script.

```js
// One Codex exec: wait for an existing CommandId and print only the terminal state.
const profile = "pro", region = "ap-southeast-1";
const commandId = "<COMMAND_ID>", instanceId = "<INSTANCE_ID>";
const code = `
r = await call_boto3(service_name='ssm', operation_name='GetCommandInvocation',
    region_name='${region}', params={'CommandId': '${commandId}', 'InstanceId': '${instanceId}'})
result = {k: r.get(k) for k in ('Status', 'StatusDetails', 'ResponseCode')}
result['stdout_tail'] = (r.get('StandardOutputContent') or '')[-2000:]
result['stderr_tail'] = (r.get('StandardErrorContent') or '')[-1000:]
result`;
const RUNNING = ["Pending", "InProgress", "Delayed"];
const deadline = Date.now() + 15 * 60 * 1000;   // set from the command's own timeout
let last = null, readErrors = 0;
while (true) {
  const res = await tools.mcp__aws_sigv4__aws___run_script({ aws_profile: profile, code });
  const rv = res?.structuredContent?.return_value;
  if (rv) { last = rv; if (!RUNNING.includes(rv.Status)) break; }
  else if (++readErrors > 5) { last = { Status: "READBACK_UNAVAILABLE", last }; break; } // read failure: never resend
  if (Date.now() > deadline) { last = { Status: "WAIT_DEADLINE", last }; break; }
  await new Promise(r => setTimeout(r, 30000));
}
text(JSON.stringify(last));
```

- `READBACK_UNAVAILABLE` or `WAIT_DEADLINE` means the outcome is unknown. Read
  that exact `CommandId` again later; it never authorizes another send.
- When full stdout/stderr is required evidence, fetch it once at terminal
  state into the run's private evidence file. Keep it out of the model-visible
  print.

## References

Load only what is needed:
- `references/operation-contract.md`
- `references/failure-map.md`
- `references/examples.md`
