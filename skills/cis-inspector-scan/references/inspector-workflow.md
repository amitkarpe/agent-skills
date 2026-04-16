# Inspector CIS Workflow

## Validity rule

A scan result is only valid when both conditions are true:
- `status = COMPLETED`
- `totalChecks > 0`

Never accept a result that fails either condition.

## Preflight sequence

Run in order before creating any scan:

1. Confirm AWS profile, account, and region
2. Confirm target instance exists and is running
3. Confirm SSM managed state (`amazon-ssm-agent` healthy)
4. Confirm IAM — instance profile must include:
   - `AmazonSSMManagedInstanceCore`
   - `AmazonInspector2ManagedCisPolicy` (managed policy, not inline)
5. Confirm VPC endpoints exist with Private DNS enabled:
   - `inspector2`, `inspector-scan`, `ssm`, `ssmmessages`, `ec2messages`, `s3`
6. Confirm metadata options:
   - `HttpEndpoint = enabled`
   - `InstanceMetadataTags = enabled`
7. Confirm unique `instance_id=<instance-id>` tag on the instance
8. Confirm subnet has free IPs if creating new endpoints

## Scan creation rules

- Use `accountIds = ["SELF"]` — do not use the literal account ID
- Target by unique tag: `instance_id=<instance-id>`
- Create one isolated config per target — avoid overlapping configs
- Save raw config JSON immediately after creation

## Recovery rule

If a `scanConfigurationArn` is already known:
- skip creation
- query scan rows by that ARN directly
- save a recovery note in the output dir

## Polling rules

- Poll every 60 seconds
- Normal completion: 2–5 minutes for a single instance
- A short `IN_PROGRESS` period with `totalChecks = 0` is normal
- Stop when: valid result, scan fails, or a clear readiness blocker is found
- Do not poll blindly beyond 15 minutes without rechecking readiness

## Fetch pattern

Query scan rows by `scanConfigurationArn`:

```bash
aws inspector2 list-cis-scans \
  --filter-criteria '{"scanConfigurationArnFilters":[{"comparison":"EQUALS","value":"<configArn>"}]}' \
  --profile <profile> --region <region>
```

Scan row may not appear immediately after config creation — wait and retry.

## Result fetch pattern

```bash
aws inspector2 list-cis-scan-results-aggregated-by-checks \
  --scan-arn <scanArn> \
  --profile <profile> --region <region>
```

## Failure map

| Symptom | Likely cause | Action |
|---|---|---|
| `totalChecks = 0` | Metadata tags disabled, wrong accountIds, IAM gap, endpoint/DNS issue | Check each in order |
| `Failed to get instance tags from instance metadata` | `InstanceMetadataTags` not enabled | Enable and wait for `applied` state |
| `ConflictException` | Another scan config targets this instance | Delete conflicting configs, wait 15s, retry |
| `status = FAILED` | SSM unhealthy or IAM missing `AmazonInspector2ManagedCisPolicy` | Fix IAM/SSM, retry |
| `InvalidPlatform` | Historical artifact | Check newest Inspector plugin logs instead |

## Plugin log location

When `totalChecks = 0`, always check the Inspector plugin log on the instance:

```
/var/log/amazon/inspector/scitor.log.<YYYY-MM-DD-HH>
```

This log contains the exact error from the plugin side.

## Evidence to save

Always save:
- `preflight.json` — preflight check results
- `scan-config.json` — raw scan configuration
- `scan.json` — raw scan row (status, counts, ARNs)
- `aggregated-checks.json` — full aggregated check results
- `failed-controls.json` — reduced: only checks with `statusCounts.failed > 0`

Store under: `~/.AGENTS-temp/<repo>/inspector-<timestamp>/`

## Result reduction rule

Inspector scans the full benchmark set. Do not confuse:
- `totalChecks` = full benchmark scope (e.g. 289)
- `failedChecks` = failed subset (e.g. 12)

Reduction steps:
1. Fetch full aggregated check output
2. Save raw JSON
3. Filter locally to checks where `statusCounts.failed > 0`
4. Save filtered JSON as `failed-controls.json`
