# HTML Mode

HTML is requested only, not default.

Publish the local cockpit to `/opt/crypto-web/demos/<slug>/index.html` and
return `http://home/demos/<slug>/` after validating the exact URL.

Keep source and evidence under
`~/.AGENTS-temp/<repo>/change-explainer/`.

Required visual sections:

- Why this change matters
- before -> after
- path / flow / direction
- file changes
- infra/resource changes
- evidence
- validation
- risks/gates
- next step

Design:

- dark local HTML by default
- broad blocks/cards
- inline SVG or CSS flow lines
- emojis allowed for Amit-only local reports
- no remote assets or CDN for MVP
- full resource IDs are allowed for local Amit HTML, but mask account IDs unless
  explicitly asked
