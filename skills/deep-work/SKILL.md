---
name: deep-work
description: premium dd deep work dashboards for durable learning, dense technical concepts, long research, multi-source synthesis, architecture reviews, cloud/aws/devops workflows, timelines, lifecycles, command cookbooks, glossary, flashcards, quizzes, and study mode. use when user says dd, deep-work, deep dashboard, learning dashboard, explain deeply, absorb this, compare research, or multi-page dashboard. not for quick task summaries.
---

# Deep Work

Create premium DD Deep Work dashboards for long-term learning and durable technical understanding.

## Use this skill for

- Prompts containing: `DD`, `deep-work`, `deep dashboard`, `learning dashboard`, `explain deeply`, `absorb this`, `study mode`, `compare research`, `multi-page dashboard`.
- Dense technical topics, codebases, architecture reviews, research, cloud/AWS/DevOps concepts, incident lessons, lifecycle learning, and long notes.
- Cases where the user wants to understand the same material through multiple visual forms.

## Do not use this skill for

- Quick operational reports. Use `web-html-page`.
- Medium visual diagrams or plan explanations. Use `visual-explainer`.

## Output contract

- Publish durable output to `/opt/agent-web/deep/<category>/<topic>/<slug>.html`.
- Store source/evidence in `~/.AGENTS-temp/deep-work/<category>/<topic>/`.
- Print a LAN URL like `http://192.168.0.9/deep/<category>/<topic>/<slug>.html`.
- Lifecycle: never auto-delete. These are durable personal learning artifacts.

## Dashboard shape

Use a premium but disciplined structure:

1. Hero thesis and 30-second view.
2. Sticky navigation with compact utility controls.
3. Snapshot cards.
4. Concept map or architecture map.
5. Workflow, lifecycle, timeline, or sequence.
6. Comparison matrix or decision guide.
7. Deep dives using collapsible sections.
8. Glossary, flashcards, quiz, and what-to-remember section.
9. Optional command cookbook with copy-safe CommandBlocks.

## Architecture Lens

DD is generic first, but architecture-aware. If the prompt mentions architecture, AWS, AMI factory, DEV/PROD, VPC, EC2, AMI, KMS, IAM, SSM, launch templates, deployment flow, or environment boundaries, add an Architecture Lens unless the user asks for a lighter page.

Architecture Lens may include:

- DEV / PROD / shared security boundary map.
- Resource lineage: source AMI → custom AMI → snapshot/KMS → launch template → EC2.
- Swimlanes for Dev, Security, Prod, Operations, and Cleanup.
- Lifecycle timeline: build → harden → test → promote → deploy → rollback window → TTL cleanup.
- Security overlay for IAM, KMS, network, audit, SSM, secrets, and compliance.
- Failure-mode bank and validation matrix.

## Design rules

- Default theme: Midnight. Optional compact icon-only toggle to Contrast.
- Use emoji as visual anchors, not decoration overload.
- Keep dense text behind collapsible deep dives.
- Use inline SVG/CSS diagrams by default. Use external architecture tools only when explicitly asked.
- No CDN, external JS, remote fonts, or remote images by default.

## Safety rules

- Do not leak secrets, credentials, private keys, tokens, session data, or production-sensitive values.
- Do not invent real AWS IDs. Unknown IDs must be labeled `unknown / needs refresh`.
- Sanitize account IDs and credential-like values unless the user explicitly approves keeping them.
- Separate concept examples from real resource evidence.

See `references/dashboard-patterns.md`, `references/architecture-lens.md`, and `assets/deep-work-template.html` only when deeper template guidance is needed.
