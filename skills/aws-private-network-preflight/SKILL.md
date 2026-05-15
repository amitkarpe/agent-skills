---
name: aws-private-network-preflight
description: Use when AWS work involves GCC, GovTech, restricted, private-only, Nexus-VPCE-sharing, TGW, VPC peering, or similar networking changes where public Internet exposure must be blocked by default. Runs a short public-exposure preflight, forces private-only alternatives first, and stops before any IGW, NAT, public subnet, public IP, EIP, internet-facing load balancer, or default Internet route unless Amit explicitly approved that exact resource type.
---

# AWS Private Network Preflight

Use this skill before AWS-mutating work in GCC, GovTech, restricted,
private-only, Nexus-VPCE-sharing, TGW, VPC peering, or similar network lanes.

## Core rule

Default deny public Internet exposure.

If the task would require any public-exposure resource to work, stop and say:

- blocked by private-network guardrail
- needs private-only redesign or explicit Amit approval

## Hard block list

Do not create, apply, or propose as fallback:

- Internet Gateway (`igw`)
- NAT Gateway
- egress-only Internet Gateway
- public subnet
- EC2 with public IP
- Elastic IP
- internet-facing ALB or NLB
- `0.0.0.0/0` or `::/0` route to IGW or NAT
- public SSH or RDP access

## Required preflight

Before any AWS mutation, write this line into the plan, goal, or pre-mutation
note:

`Public exposure check: IGW=no, NAT=no, public subnet=no, public IP=no, EIP=no, internet-facing LB=no, default route to IGW/NAT=no`

If any field would be `yes`, stop before apply unless Amit explicitly approved
that exact resource type.

## Preferred private alternatives

Prefer these first:

- private subnets
- VPC endpoints / PrivateLink
- Transit Gateway
- VPC peering
- approved private proxy path
- SSM Session Manager instead of public SSH

## Cleanup rule

If a mistaken public-exposure test lane already exists:

1. freeze changes
2. capture dependency evidence
3. delete in safe dependency order
4. verify removal with direct AWS APIs
5. save evidence under `~/.AGENTS-temp/<repo>/`
