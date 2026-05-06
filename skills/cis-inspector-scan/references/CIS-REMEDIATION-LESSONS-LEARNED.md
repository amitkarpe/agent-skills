# CIS Remediation — Lessons Learned (CloudOS AL2, 2026-04-12)

## What the SSM doc track achieved

Starting point: 40 failures
After v21: **9 failures / 289 checks**

Permanent floor via SSM: 9 failures
- 5 partition controls (structural — AMI-only fix)
- 4 platform/scanner-parity exceptions (accept risk)

---

## Controls that look fixable but aren't (via SSM)

### `3.4.4.2.1` + `3.4.4.2.4` — ip6tables loopback + default deny

These fail because `net.ipv6.conf.all.disable_ipv6=1` is set via sysctl.
With IPv6 disabled, ip6tables loads but Inspector treats the config as inconsistent.

Attempted fixes:
- Remove `disable_ipv6` from kernel args → ip6tables loads → `3.4.4.2.1/2.4` still fail
- Remove `disable_ipv6` from sysctl → ip6tables fully active → opens 2 NEW failures (`3.4.4.3.1`, `3.4.4.3.3`)
- Insert loopback rules at position 1 → Docker re-inserts its rules on top after start

**Conclusion:** These 2 controls are a scanner-parity dead end for Docker-running instances. Accept risk.

### `1.5.1.6` — unconfined services

Nessus agent runs as `unconfined_service_t`. SSM agent has no SELinux policy.
Cannot fix without removing these agents. Accept risk.

### `3.3.1` — ip_forward

Docker sets `net.ipv4.ip_forward=1` on start. Cannot prevent without breaking Docker. Accept risk.

---

## Controls that were fixed (key lessons)

### `5.2.3.19` — kernel module collection

**Root cause:** Rule used `auid!=-1` without `auid>=1000`, and key was `modules` not `kernel_modules`.
**Fix:** Separate each syscall into its own rule, add `auid>=1000`, use key `kernel_modules`.
**Source of truth:** CIS Level 2 Marketplace AMI audit rules — extract and compare directly.

### `3.4.4.2.1/2.4` — ip6tables (partial)

**Root cause:** `ipv6.disable=1` in kernel cmdline prevents ip6tables from initializing.
**Fix:** Remove from kernel args, keep in sysctl. ip6tables loads but controls still fail (see above).

### `5.1.4` — logfile permissions

**Root cause:** Permissions reset on reboot (wtmp, dmesg, cloud-init.log written by kernel/cloud-init).
**Fix:** Systemd oneshot service (`cloudos-log-perms.service`) runs after boot and re-applies 640.

---

## The Marketplace Level 2 AMI approach

AMI: `ami-02abdc573a643de13` (CIS AL2 Kernel 5.10 Level 2 v03, ap-southeast-1)
Baseline score: **8 failures / 289** (all 5 partition controls pass)

Key differences from SSM-hardened instance:
- LVM with separate partitions baked in — closes all 5 partition controls
- 120 audit rules pre-loaded with correct `auid!=unset` form
- No `ipv6.disable=1` in kernel args — ip6tables works correctly
- `/var` = 10GB, LVM VG fully allocated — must increase to 60GB for ECS workloads

**Subscription:** Console-only per account. No CLI/API bypass.
**Copy:** AMI product code follows all snapshot lineage — each account must subscribe independently.

Projected derived AMI score: **2 failures** (platform exceptions only).

---

## Audit rule parity — critical insight

The CIS AMI uses `auid!=unset` throughout.
AL2 kernel translates `unset` to `-1` internally — they are equivalent at kernel level.
But Inspector checks the **string** in the rule, not the kernel behavior.

**Always use `auid!=unset` in audit rules, never `auid!=-1`.**

Also: Inspector checks key names exactly. `modules` ≠ `kernel_modules`.
Always extract rules from the reference AMI and compare character-by-character.
