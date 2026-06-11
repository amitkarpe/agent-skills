---
name: visual-explainer
description: medium visual html explanation reports for architecture, workflows, sequences, resource relationships, ami boxes, plan proposals, option comparisons, before/after maps, and explain visually requests. use when the user needs understanding through diagrams, inline svg, concept-to-real-resource mapping, or aws relationships. richer than web-html-page, lighter than deep-work. avoid durable learning dashboards.
---

# Visual Explainer

Create medium-weight visual HTML reports that explain a technical idea, workflow, architecture, plan, or before/after change.

## Use this skill for

- Prompts containing: `explain visually`, `visual explainer`, `architecture diagram`, `workflow diagram`, `AMI box`, `plan proposal`, `compare options`, `show sequence`, `before/after`.
- Understanding system design, resource relationships, build flows, deployment sequences, or decision logic.
- A report that needs diagrams but not a large durable DD learning dashboard.

## Do not use this skill for

- Fast operational summaries. Use `web-html-page`.
- Long-term study artifacts, multi-page learning, flashcards, or research synthesis. Use `deep-work`.

## Output contract

- Publish HTML to `/opt/agent-web/<project-or-repo>/<current-lane>/<slug>.html`.
- Store source/evidence in `~/.AGENTS-temp/<project-or-repo>/<current-lane>/visual-explainer/`.
- Print a LAN URL like `http://192.168.0.9/<project-or-repo>/<current-lane>/<slug>.html`.
- Default lifecycle: archive after 30 days unless marked `keep`.

## Visual report shape

Use only the components needed:

1. Hero with the problem and the mental model.
2. Snapshot cards for key facts.
3. Inline SVG diagram as the default visual method.
4. Concept-to-real-resource mapping when examples exist.
5. Workflow, sequence, decision tree, or before/after map.
6. Risks, unknowns, and validation evidence.
7. Short recap or action checklist.

For AWS examples, separate concept from real resources. If a real ID, ARN, IP, AMI ID, instance ID, account ID, or tag is unavailable, mark it `unknown / needs refresh`. Never invent realistic identifiers.

## Diagram guidance

Prefer inline SVG or CSS diagrams. Use Mermaid only if vendored locally or explicitly requested. Do not use remote CDN assets.

Useful patterns:

- Workflow: trigger → build → test → promote → deploy → cleanup.
- Architecture map: environment boundary → service/resource cards → arrows.
- AMI box: base AMI → hardening/tools → custom AMI → launch template → EC2.
- Sequence flow: actor → system → service → result.
- Decision tree: condition → option → risk → recommendation.

## Safety rules

- No secrets, credentials, tokens, private keys, or unmasked sensitive data.
- Sanitize or mask AWS account-sensitive values by default.
- Label examples clearly as `example`, `placeholder`, or `unknown`.
- Keep the report self-contained, offline, and local LAN safe.

See `references/visual-patterns.md`, `references/aws-resource-safety.md`, and `assets/visual-explainer-template.html` only when needed.
