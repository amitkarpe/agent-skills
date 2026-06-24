# Architecture Design Diagram Guide

Purpose: choose the right diagram method for architecture, workflow, and Ops
presentations without rediscovering the same tool tradeoffs.

This is the short operating guide. For deeper DD/dashboard patterns, use:

- `skills/deep-work/references/architecture-lens.md`
- `skills/visual-explainer/DESIGN.md`

## Quick Decision

| Need | Use | Why |
| --- | --- | --- |
| Amit/team presentation | custom HTML following `visual-explainer` design | Best visual control and easiest to make impressive. |
| AWS architecture PNG with real service icons | Python `diagrams` | Good AWS/service icons and reproducible source. |
| Export-safe portal diagram for HTML and DOCX | Graphviz/DOT to SVG plus PNG | Deterministic and reliable for DOCX embedding. |
| Medium visual report | `visual-explainer` JSON renderer | Fast, safe, repeatable, but less custom. |
| Durable multi-page learning/KB | `deep-work` | Best for deep explanation, portal, glossary, timeline, and export. |
| Kiro/QW assistance | scratch-only critique or first draft | Useful for ideas, but Codex owns cleanup and final output. |

## Five-Block Presentation Rule

For Amit-facing technical presentations, start with five blocks:

1. Real progress or proof.
2. Main visual mental model.
3. Concrete code path.
4. Runtime/Ops workflow.
5. Team talk track or decisions.

Do not start with tool comparison. First make one useful visual baseline.

## Quality Bar

Every final architecture diagram should have:

- clear title
- one main story
- visible environment/resource boundaries
- short readable labels
- legend or obvious color meaning
- real progress/proof separated from future plans
- no invented resource IDs
- no secrets or private values
- reproducible source
- output suitable for the target: HTML, PNG, SVG, DOCX, or presentation

## Python `diagrams` Rules

Use Python `diagrams` when the user asks for:

- AWS icons
- proper architecture PNG
- service relationship picture
- Kiro/Python diagram graph module

Lessons from the Nextflow offline Kiro spike:

- Use `diagrams.onprem`, not `diagrams.onpremise`.
- Check imports before asking Kiro to write code:
  - `python3 -c "import diagrams; print(diagrams.__file__)"`
  - `python3 -c "from diagrams.onprem.vcs import Gitlab"`
- A light canvas works better for Python `diagrams`; dark canvas caused
  low-contrast or clipped labels.
- Keep labels short.
- Use real icons only where they improve recognition.
- Reduce cross-edges aggressively.
- Group details into bundle nodes when the real graph becomes noisy.
- Render at least three passes before calling it final.

Good iteration pattern:

1. v1: get the rough concept.
2. v2: replace generic nodes with real icons.
3. v3: reduce clutter and cross-edges.
4. final: choose presentation diagram and code-walkthrough diagram separately.

## Kiro/QW Rules

Use Kiro/QW for diagram work only in scratch directories.

Safe pattern:

```bash
mkdir -p /tmp/offline-diagram-spike
cd /tmp/offline-diagram-spike
kiro-cli chat --legacy-ui
```

Do not run trusted Kiro from inside a real git repo unless you are prepared for
it to write files there.

When using Kiro:

- give one bounded diagram task
- require output under the current scratch directory
- save the prompt and raw output under `~/.AGENTS-temp/<repo>/`
- render and inspect the result yourself
- Codex decides final quality

## Graphviz/DOT Rules

Use Graphviz/DOT when:

- the diagram must be deterministic
- HTML and DOCX export both matter
- labels and layout should be repo-owned
- a portal needs stable diagram assets

Recommended outputs:

- `.dot` source
- `.svg` for browser
- high-DPI `.png` for DOCX

Known issue:

- Orthogonal edge labels can become noisy. Prefer fewer edge labels, `xlabel`,
  or node labels when the diagram gets crowded.

## Custom HTML Rules

Use custom HTML when Amit says the page must be impressive, visual, or
presentation-ready.

Follow `visual-explainer` Midnight Visual rules unless the target is a Python
`diagrams` PNG. For presentations:

- keep five blocks
- use one strong diagram
- use high contrast and large labels
- put the concrete code flow on the page
- show decisions and progress, not just architecture theory

## File Layout

Scratch:

```text
~/.AGENTS-temp/<repo>/diagram-spike/
/tmp/<topic>-diagram-spike/
```

Published HTML:

```text
/opt/agent-web/<project>/<lane>/<slug>.html
```

Repo-owned diagrams, only after review:

```text
docs/diagrams/<topic>/
  README.md
  <diagram>.py
  <diagram>.dot
  <diagram>.svg
  <diagram>.png
```

## Final Rule

The best diagram is not the prettiest raw image. The best diagram is the one
that helps Amit explain real work, real code, real runtime behavior, and the
next decision with the least confusion.
