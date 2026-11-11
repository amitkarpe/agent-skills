# Failure map

Common failure patterns:

- `InvocationDoesNotExist`
  - often transient just after send
  - `ssm_wait.sh` retries this for the configured initial window
- `ThrottlingException`
  - transient
  - `ssm_wait.sh` retries this for the configured initial window
- `InternalServerError`
  - transient
  - `ssm_wait.sh` retries this for the configured initial window
- terminal non-success:
  - `Cancelled`
  - `TimedOut`
  - `Failed`

Common operator checks:

- instance is SSM online
- command text is valid and not empty
- correct region/profile
- IAM allows:
  - `ssm:SendCommand`
  - `ssm:GetCommandInvocation`
  - `sts:GetCallerIdentity`

Lessons from aws-factory #53 (4 Nov 2026):

- `Failed/1` after some stdout, with `set -euo pipefail`: a `grep` that finds no line ends the whole run.
  A `--quiet` flag can hide the line that `grep` looks for (`mongorestore --quiet` hides "restored successfully").
  Add `|| true` after an optional `grep`, or test the tool's own exit code.
- Secrets on the host: never pass a password as an argument (`-p "$P"`, a URI with the password). Other users see it in `ps`.
  Read it into an environment value and let the tool read it (`mongosh --nodb` with `process.env.X`).
- `ssm_run.sh` writes the result under `.Output` (`.Output.Status`, `.Output.StdOut`). `jq .Status` gives `null`.
