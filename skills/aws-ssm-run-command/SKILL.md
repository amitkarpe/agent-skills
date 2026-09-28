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

## Script Usage

- `scripts/ssm_send.sh`: send command and print `CommandId`
- `scripts/ssm_wait.sh`: wait loop with transient retry window
- `scripts/ssm_get_output.sh`: fetch final invocation output
- `scripts/ssm_run.sh`: orchestration wrapper returning normalized JSON

## References

Load only what is needed:
- `references/operation-contract.md`
- `references/failure-map.md`
- `references/examples.md`
