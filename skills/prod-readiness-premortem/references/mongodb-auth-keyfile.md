# MongoDB Auth / KeyFile PROD Pre-Mortem Addendum

Use this reference for MongoDB replica-set auth, keyFile, and application
connectivity changes.

## Failure Modes To Attack

- Admin credential is not proven before enabling auth.
- Admin credential exists in DEV but PROD SSM path, KMS key, IAM decrypt, or
  username differs.
- KeyFile value or file permissions differ across members.
- `transitionToAuth` is left enabled or removed too early.
- Health checks keep using unauthenticated commands after auth enforcement.
- Primary changes during rollout and the operator restarts the wrong member.
- A secondary does not rejoin but the rollout continues.
- App connection strings omit auth source, replica set name, TLS setting, or
  credentials needed after auth.
- GitLab or another client does not retry cleanly after stepdown/election.
- Backup host has tools but backup or restore with auth has not been proven.
- Rollback path requires unauthenticated access that no longer exists.
- Logs/monitoring do not distinguish auth failures from network failures.
- Temp validation DB/user remains after the smoke test.

## Required PROD Evidence Before Go

- Target account, region, VPC, subnet, SG, DNS, and SSM paths are named.
- PROD SSM SecureString metadata exists; secret values are not printed.
- IAM role used by automation can decrypt/read only required SSM parameters.
- All MongoDB nodes are running, private-only, SSM Online, and healthy.
- Current primary/secondaries are discovered immediately before rollout.
- Existing config state is known on every node.
- Client/app connection behavior during stepdown is understood.
- Backup authentication and restore/readback expectation are defined.
- Rollback trigger and exact rollback steps are written before mutation.

## PROD No-Go Gates

- Wrong account or region.
- Any public IP or public exposure appears.
- Any required SSM/KMS decrypt fails.
- Admin auth cannot be proven before first keyFile-enabled restart.
- Replica set is not one PRIMARY plus expected SECONDARY members with health=1.
- A changed node does not rejoin healthy before the next node.
- App connectivity fails in a way that is not understood.
- Backup/auth validation fails and backup is required for the window.
- Rollback steps are not executable by the on-call operator.
