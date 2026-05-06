---
name: aws-ssm-run-command
description: Use this skill when users ask to run AWS Systems Manager Run Command (send-command/get-command-invocation), wait for terminal status, and collect stdout/stderr evidence with a reliable wrapper flow.
---

# AWS SSM Run Command

## Overview

Use this skill for reliable AWS SSM Run Command operations with a fixed contract:
- send command payload safely
- wait with transient retry handling
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

1. Build a command file with bash-safe commands.
2. Run `scripts/ssm_send.sh` for command dispatch.
3. Run `scripts/ssm_wait.sh` until terminal status.
4. Run `scripts/ssm_get_output.sh` for stdout/stderr.
5. Prefer `scripts/ssm_run.sh` for one-shot execution.

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
