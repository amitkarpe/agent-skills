# Docker awslogs credential-refresh failure

Known ECS-on-EC2 failure pattern:

- Docker `awslogs` cannot create or initialize CloudWatch log streams
- repeated errors in `journalctl -u docker`
- common messages:
  - `failed to create Cloudwatch log stream`
  - `failed to refresh cached credentials`
  - `failed to load credentials`
  - `retry quota exceeded`

## Important operational read

- ECS services can remain healthy while task logs are still failing to reach CloudWatch.
- The problem can be node-local and uneven across the cluster.
- A clean node does not prove cluster-wide recovery.

## Proven signals

- compare loaded older nodes against a clean node
- inspect Docker journal, not just CloudWatch log group presence
- correlate failing nodes with current task placement

## What not to assume

- do not assume Docker restart is a durable fix
- do not assume ECS agent version alone explains the issue
- do not assume service health means logging health

## Preferred mitigation order

1. identify the failing node set
2. set one failing node to `DRAINING`
3. wait for service recovery elsewhere
4. if needed, use Docker/ECS restart only as a diagnostic step
5. prefer node replacement or long-lived drain over putting a still-failing node back into service

## One-node outcome seen in prod

In a real prod check on `2026-04-22`:

- node was drained successfully
- Docker and ECS were restarted
- fresh `awslogs` credential-refresh errors still appeared after restart

Conclusion:

- drain/replacement is safer than treating restart as a fix
