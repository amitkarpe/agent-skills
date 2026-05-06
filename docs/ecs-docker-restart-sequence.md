# ECS Docker Restart Sequence

Safe sequence for ECS EC2 hosts when Docker networking state must be rebuilt.

## Use when

- Docker NAT chains are missing or corrupted
- ECS task port publishing fails
- `iptables -t nat` lost the `DOCKER` chain

## Do not do

- do not restart Docker on all nodes in parallel
- do not restart Docker before capturing the current state
- do not restart Docker without restarting ECS afterward

## Safe rolling sequence

1. Pick one ECS container instance only.
2. Capture before state:
   - `systemctl is-active docker`
   - `systemctl is-active ecs`
   - `iptables -t nat -S`
   - `docker ps`
3. Restart in this order:
   - `systemctl restart docker`
   - wait 10 seconds
   - `systemctl restart ecs`
4. Verify after restart:
   - `docker=active`
   - `ecs=active`
   - `iptables -t nat -S` contains `-N DOCKER`
   - `docker ps` returns cleanly
5. Wait 60 seconds and check service health before moving to the next node.

## Stop conditions

- Docker does not return
- ECS does not return
- `DOCKER` chain is missing
- cluster health clearly worsens after a node restart

## Why the sequence matters

- Docker recreates NAT state needed for ECS task port mappings
- ECS should restart only after Docker networking is back
- restarting all nodes in parallel increases blast radius and can collapse the cluster
