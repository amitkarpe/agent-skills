# CIS Skills — Bugs Found and Fixed (Live Session 2026-04-12)

## Bug 1: `get-cis-scan-configuration` does not exist

**Script:** `inspector_cis_create_or_recover_scan.sh`
**Symptom:** Script exits non-zero immediately after creating the scan config.
**Root cause:** AWS CLI has no `get-cis-scan-configuration` subcommand.
**Fix:** Replace with `list-cis-scan-configurations` + JMESPath filter:
```bash
aws inspector2 list-cis-scan-configurations \
  --query "scanConfigurations[?scanConfigurationArn=='$ARN'] | [0]" \
  --output json
```

---

## Bug 2: `--filter-criteria` JSON quoting breaks in bash → infinite poll loop

**Script:** `inspector_cis_fetch_results.sh`
**Symptom:** Poll loop runs forever, `SCAN_COUNT=0` every iteration, never exits.
**Root cause:** Inline JSON string passed to `--filter-criteria` gets mangled by bash quoting. AWS CLI receives a malformed argument and returns an empty list silently.
**Fix:** Use `list-cis-scans` without `--filter-criteria`, filter in Python by matching config ARN:
```bash
SCAN_LIST=$(aws inspector2 list-cis-scans --output json)
SCAN_ROW=$(echo "$SCAN_LIST" | python3 -c "
import sys,json
scans=json.load(sys.stdin).get('scans',[])
match=[s for s in scans if s.get('scanConfigurationArn')=='$SCAN_CONFIG_ARN']
print(json.dumps(match[0]) if match else '')
")
```

---

## Bug 3: Stale scan configs cause silent `ConflictException` → `totalChecks=0`

**Script:** `inspector_cis_create_or_recover_scan.sh`
**Symptom:** New scan completes with `status=COMPLETED, totalChecks=0`. Inspector plugin log shows `ConflictException: target is already part of another scan`.
**Root cause:** Every cancelled run leaves a scan config behind. The next run creates a new config but the Inspector plugin on the instance sees a conflict and exits without scanning.
**Fix:** Before creating, auto-delete any existing configs targeting the same `instance_id` tag:
```bash
EXISTING=$(aws inspector2 list-cis-scan-configurations --output json | python3 -c "
import sys,json
data=json.load(sys.stdin)
arns=[c['scanConfigurationArn'] for c in data.get('scanConfigurations',[])
      if '$INSTANCE_ID' in c.get('targets',{}).get('targetResourceTags',{}).get('instance_id',[])]
print(' '.join(arns))
")
for ARN in $EXISTING; do
  aws inspector2 delete-cis-scan-configuration --scan-configuration-arn "$ARN"
done
[ -n "$EXISTING" ] && sleep 15
```

---

## Bug 4: `inspector_cis_reduce_failed_controls.sh` reads wrong JSON key

**Script:** `inspector_cis_reduce_failed_controls.sh`
**Symptom:** Script iterates over an empty list or crashes.
**Root cause:** `aggregated-checks.json` is a dict `{"checkAggregations": [...]}` but the script treated it as a raw list.
**Fix:**
```python
data = json.load(f)
checks = data.get("checkAggregations", data) if isinstance(data, dict) else data
```

---

## Bug 5: Poll ceiling too high (20 min) — should be 5 min

**Script:** `inspector_cis_fetch_results.sh`
**Symptom:** Loop runs for 20 minutes before timing out. Single-instance scans complete in 2-5 min.
**Fix:** Change defaults:
```bash
POLL_INTERVAL=30   # was 60
MAX_POLLS=10       # was 20 → 5 min ceiling
```
Always implement a recovery path: if fetch times out, wait 60s and call the script again with `--scan-config-arn` (recovery mode). The scan will have completed by then.
