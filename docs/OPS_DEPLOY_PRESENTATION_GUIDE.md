# Ops Deploy Presentation Guide

Use this guide for AWS deployment presentations intended for operators who
should understand the decision and click path without learning the underlying
Terraform, Terragrunt, AWS CLI, or orchestration internals.

## Reusable rules

1. Choose the smallest useful format.
   - Use `web-html-page` for a five-minute operational briefing.
   - Use `visual-explainer` for one rich architecture and workflow story.
   - Use `deep-work` for a durable multi-page Ops portal or training package.

2. Use the five-block story.
   - Current live state.
   - Proposed change.
   - AWS execution path.
   - Expected after state.
   - Gates, evidence, and next action.

3. Put current readiness on the first screen. Never make a future Deploy button
   look live. State the exact blocker and the next proof needed before the
   operator reads the detailed architecture.

4. Label every important claim as `PROVEN`, `IMPLEMENTED`, `BLOCKED`, or
   `FUTURE`.
   - `PROVEN`: observed runtime evidence exists.
   - `IMPLEMENTED`: versioned code exists and checks pass, but runtime proof may
     remain.
   - `BLOCKED`: a named gate prevents the next proof.
   - `FUTURE`: design intent, not current capability.

5. Show real AWS responsibility boundaries. For an ECS AMI deploy, explain the
   whole relationship: operator trigger -> CodeBuild -> SSM Automation -> launch
   template version -> ASG instance refresh -> ECS capacity provider -> ECS
   services and tasks -> evidence. Include container-instance draining and
   warm-up alignment when instance replacement is involved.

6. Separate the concept from real resources. Use friendly component names in
   the main diagram, then map them to verified resource names in a table. Mark
   missing live identifiers as `unknown / needs refresh`; never invent them.

7. Teach with at least three outcomes: normal deploy, preflight/IAM stop, and
   runtime health stop. Describe recovery or operator escalation only as far as
   the approved runbook supports; do not invent automatic rollback behavior.

8. Show the evidence packet the operator will receive. Include the execution
   identifier, before/after launch template version, instance refresh result,
   AMI on replacement nodes, ECS desired/running service proof, and retention
   location. A redacted or clearly labelled example is acceptable before the
   first successful run.

9. Keep generation deterministic and offline. Prefer JSON-spec renderers or a
   versioned generator. Embed diagrams and images; do not use remote fonts,
   scripts, CDNs, or image URLs. Sanitize AWS account identifiers and secrets.

10. Validate the artifact as a user would see it. Run static HTML checks and,
    for rich or shared output, capture desktop and mobile Playwright
    screenshots. Check text fit, contrast, horizontal overflow, nav links,
    proof labels, and that diagrams remain readable.

## Kiro-independent toolchain

The durable workflow must not depend on a paid Kiro session:

- Python `diagrams` plus Graphviz: reproducible AWS-icon PNG generation.
- draw.io desktop CLI: editable diagram source and deterministic PNG/PDF export.
- Playwright plus Chromium: desktop/mobile screenshot and overflow QA.
- AWS CLI plus `jq`, `jaq`, or `yq`: deterministic evidence collection when AWS
  reads are explicitly allowed.
- AWS documentation, API, pricing, and architecture MCP servers through any
  approved MCP client: current reference material without Kiro-specific state.
- Repo-owned Markdown skills and generator scripts: durable prompts, design
  rules, and render contracts available to Codex, PAT, TD, and AA.

Treat Kiro as an optional reviewer for current AWS knowledge. Keep its session
history, converted hooks, and credit-dependent behavior out of the trusted
execution path.

## Acceptance checks

- The first screen states current readiness and the exact next gate.
- Every runtime claim has a proof-state label and evidence source.
- The diagram includes the control plane, ASG/ECS capacity bridge, health path,
  and evidence path.
- The artifact has no remote assets, secrets, invented identifiers, or hidden
  content required for the decision.
- Desktop and mobile screenshots are readable without incoherent overlap or
  horizontal scrolling.
