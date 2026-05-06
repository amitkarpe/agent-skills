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
