# Source Artifacts

Proven scan examples used to validate this skill's rules and defaults.

## Proven check counts

| Platform | Security Level | totalChecks |
|---|---|---|
| AL2 reference run | LEVEL_2 | ~229 |
| AL2023 valid run | LEVEL_2 | ~243 |
| AL2023 prod-style run | LEVEL_2 | 289 |

If `totalChecks = 0`, the scan is not valid regardless of status.

## Proven accountIds pattern

`["SELF"]` works for same-account scans.
Using the literal AWS account ID caused `totalChecks = 0` in production.

## Proven targeting pattern

```
EC2 tag: instance_id=<instance-id>
Scan config filter: { "key": "instance_id", "value": "<instance-id>" }
```

## Proven scan config shape

```json
{
  "scanName": "my-cis-scan-20260411",
  "securityLevel": "LEVEL_2",
  "targets": {
    "accountIds": ["SELF"],
    "targetResourceTags": {
      "instance_id": ["<instance-id>"]
    }
  },
  "schedule": { "oneTime": {} }
}
```

## Proven query pattern

Query by `scanConfigurationArn` is reliable:

```bash
aws inspector2 list-cis-scans \
  --filter-criteria '{"scanConfigurationArnFilters":[{"comparison":"EQUALS","value":"<configArn>"}]}' \
  --profile <profile> --region <region>
```

## Proven aggregated checks query

```bash
aws inspector2 list-cis-scan-results-aggregated-by-checks \
  --scan-arn <scanArn> \
  --profile <profile> --region <region>
```

## Proven evidence file set

| File | Description |
|---|---|
| `scan-config.json` | Raw output of `get-cis-scan-configuration` |
| `scan.json` | Raw scan row from `list-cis-scans` |
| `aggregated-checks.json` | Full output of `list-cis-scan-results-aggregated-by-checks` |
| `failed-controls.json` | Local reduction: checks where `statusCounts.failed > 0` |

## Known IAM gap

`AmazonInspector2ManagedCisPolicy` must be attached as a managed policy on the
instance role. Without it, the Inspector plugin on the instance gets
`AccessDeniedException` on `inspector2:StartCisSession`.
Symptom: `status=COMPLETED`, `totalChecks=0`, no error visible from control plane.

## Known conflict pattern

If multiple scan configs target the same instance simultaneously:
- Inspector plugin log shows: `ConflictException: target is already part of another scan`
- Fix: delete all existing scan configs for the target, wait 15s, create one clean config

## Inspector plugin log path

```
/var/log/amazon/inspector/scitor.log.<YYYY-MM-DD-HH>
```

Always check this log when `totalChecks = 0`.
