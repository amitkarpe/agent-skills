---
name: ssm-command-evidence
description: Run one AWS Systems Manager command or document on one instance, wait for completion, capture stdout/stderr/status, and save durable evidence. Use for repeated one-host AWS CLI plus SSM loops that are broader than CIS-specific document workflows.
---

# SSM Command Evidence

Use this skill for the generic one-instance SSM operator loop when you want a
durable local evidence bundle, not just a command result.

## Use when

- running one shell command on one EC2 instance through SSM
- running one existing SSM document and saving evidence
- collecting stdout, stderr, status, and timing for one host
- proving whether a host-side change succeeded before wider rollout
- saving a repeatable evidence bundle under `~/.AGENTS-temp/<repo>/...`

## Preferred workflow

1. Confirm target instance is SSM online.
2. Save the exact command or document input.
3. For `AWS-RunShellScript`, use `aws-ssm-run-command` as the core send/wait/get-output engine.
4. For an existing SSM document, keep the same durable evidence flow and use the shared wait/get-output helpers.
5. Save:
   - command id
   - status
   - stdout
   - stderr
   - target instance id
   - profile / region
6. Record the next action:
   - success
   - retry
   - rollback

## Typical AWS CLI pattern

```bash
aws ssm send-command ...
aws ssm get-command-invocation ...
aws ssm list-command-invocations ...
```

## Save evidence under

```bash
~/.AGENTS-temp/<repo>/ssm-command-evidence/<timestamp>-<instance_id>/
```

## Rules

- prefer one instance at a time first
- save the exact command input, not only the output
- do not widen to many instances until one-host proof is clean
- treat rollback as a documented next step, not an implied chat action
- treat this skill as the durable wrapper around `aws-ssm-run-command`, not a competing SSM engine
- use `cis-ssm-apply-validate` instead when the task is specifically:
  - publish/update SSM document
  - pin default version
  - apply and validate the CIS document workflow end to end

## Related skills

- `aws-ssm-run-command`
- `cis-ssm-apply-validate`
- `ami-validation-ssm`
