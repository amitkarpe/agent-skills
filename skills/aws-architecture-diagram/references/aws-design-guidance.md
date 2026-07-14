# AWS Architecture Design Guidance

## Official References

- AWS architecture icon source: `https://aws.amazon.com/architecture/icons/`
- Architecture diagramming concepts and diagram types: `https://aws.amazon.com/what-is/architecture-diagramming/`
- AWS reference architecture diagrams: `https://aws.amazon.com/architecture/reference-architecture-diagrams/`

Use reference diagrams for visual and architectural inspiration, not as evidence that the user's system contains the same services.

## Choose the View Before Drawing

| View | Show | Usually omit |
|---|---|---|
| Technical overview | actors, major services, boundaries, primary flows | instance-level detail |
| Application | frontend, APIs, compute, data, integrations | deployment tooling unless relevant |
| Deployment | accounts, Regions, VPCs, AZs, subnets, runtime units | business-process detail |
| DevOps | source, build, test, artifact, deploy, evidence, rollback | unrelated runtime internals |
| Security | trust boundaries, identity, encryption, inspection, logging | cosmetic implementation detail |
| Data flow | producers, transformations, stores, consumers, protocols | management-plane noise |
| Current/target state | clear state distinction, migration path, dependencies | unverified future claims |

## Composition Pattern

1. Place external actors and upstream systems on the left.
2. Place ingress and interfaces next.
3. Place compute and orchestration in the center.
4. Place data stores and downstream systems on the right.
5. Place security, observability, and governance below or around the primary flow.
6. Put titles on boundaries, not in the middle of data paths.

## Beautiful Does Not Mean Decorative

A high-quality AWS diagram is readable, consistent, restrained, and traceable to evidence. Avoid gradients, oversized shadows, random colors, excessive 3D/isometric shapes, decorative clouds, and unexplained icons. Use whitespace and hierarchy instead.
