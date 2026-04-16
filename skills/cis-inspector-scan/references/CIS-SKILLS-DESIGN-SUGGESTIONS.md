# CIS Skills — Design Suggestions for Future Build

## What worked well (keep)

- Preflight script is excellent — clear pass/fail per check, saves JSON, exits non-zero on failure
- Recovery mode (`--scan-config-arn`) is the right pattern — lets you resume after timeout
- Separate scripts per concern (preflight / create / fetch / reduce) is the right structure
- `accountIds: ["SELF"]` targeting works; literal account ID causes `totalChecks=0`
- `instance_id` tag targeting is reliable; `Name` tag is not

---

## Suggested new skills

### 1. `inspector_cis_full_pipeline.sh` — single-command wrapper

Wraps all 4 scripts with built-in retry/recover:
```
preflight → create (with auto-conflict-cleanup) → fetch (with auto-recover on timeout) → reduce
```
Saves all evidence to a timestamped output dir. Exits 0 only on valid result.

This is what agents actually need — one command, not 4.

### 2. `inspector_cis_cleanup.sh` — delete all configs for an instance

```bash
bash inspector_cis_cleanup.sh --profile <p> --region <r> --instance-id <i-xxx>
```

Deletes all scan configs targeting `instance_id=<i-xxx>`. Run before any new scan to guarantee clean state. Should be idempotent.

### 3. `ssm_cis_apply_and_scan.sh` — apply SSM doc + reboot + scan in one flow

```bash
bash ssm_cis_apply_and_scan.sh \
  --profile <p> --region <r> \
  --instance-id <i-xxx> \
  --ssm-doc CloudOS-CIS-Dev-Aggressive \
  --ssm-version 21 \
  --output-dir <dir>
```

Steps: send-command → poll until Success → reboot → wait SSM online → run full Inspector pipeline.
This is the entire rehearsal loop in one script.

---

## Key operational rules to encode in SKILL.md

1. **Always delete stale configs before creating** — `ConflictException` is silent, causes `totalChecks=0`
2. **Poll ceiling = 5 min (30s × 10)** — single-instance scans complete in 2-5 min
3. **Always implement recover path** — if fetch times out, wait 60s and recover by config ARN
4. **Check plugin log on `totalChecks=0`** — `/var/log/amazon/inspector/scitor.log.*` has the real error
5. **`--filter-criteria` JSON breaks in bash** — never use it; filter in Python instead
6. **Marketplace AMI subscription is console-only** — no CLI/API bypass exists
7. **`AmazonInspector2ManagedCisPolicy` must be named explicitly** — not just "confirm IAM"

---

## Suggested SKILL.md structure improvements

Current structure is good. Add these sections:

### Quick troubleshoot decision tree
```
totalChecks=0?
  → check plugin log on instance first
  → if ConflictException → run cleanup script, wait 15s, retry
  → if AccessDeniedException → add AmazonInspector2ManagedCisPolicy to instance role
  → if no log entry at all → check InstanceMetadataTags=enabled
```

### Evidence naming convention
```
<repo>/inspector-<YYYYMMDD-HHMMSS>/
  preflight.json
  scan-config.json
  scan-config-arn.txt
  scan.json
  aggregated-checks.json
  failed-controls.json
```
Always use timestamp in dir name so multiple runs don't overwrite each other.

### What `totalChecks=0` means vs `failedChecks=0`
- `totalChecks=0` = scan didn't run (readiness problem)
- `failedChecks=0` with `totalChecks=289` = scan ran and everything passed
These are completely different. Never confuse them.
