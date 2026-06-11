# Architecture Lens

Use this reference when DD needs architecture or AWS/system design depth.

## Architecture modes

- Inline CSS/SVG: default and offline-safe.
- Mermaid: optional only if vendored locally or explicitly requested.
- Python diagrams or AWS diagram tooling: mention or use only when the user asks for generated PNG/SVG architecture artifacts.

## Architecture components

- Environment boundary board: DEV, TEST, PROD, shared services, external systems.
- Resource lineage: source → transformation → artifact → consumer.
- Security overlay: identity, encryption, network, logging, secrets, compliance.
- Lifecycle timeline: build, test, promote, deploy, operate, rollback, cleanup.
- Failure-mode bank: permissions, region, sharing, KMS, SSM, TTL, rollback.
- Validation matrix: check, evidence, confidence, owner.

## AMI Factory recipe

Use this when asked about AMI Factory or EC2 image lifecycle:

1. Source AMI selected.
2. Build environment launches temporary builder.
3. Security tooling and OS hardening applied.
4. Tests and scans run.
5. Custom AMI and snapshots created.
6. AMI shared or copied to target account/region.
7. Launch template or deployment plan updated.
8. Production EC2 rollout during approved window.
9. Rollback window monitored.
10. TTL cleanup removes temporary resources.
