# Agent Web Tools

Source-owned helper scripts for deterministic local HTML publishing.

Runtime location:

- `/opt/agent-web/bin/agent-report`
- `/opt/agent-web/bin/agent-web-www`
- `/opt/agent-web/bin/agent-report-smoke`

Convenience user location:

- `~/.local/bin/agent-report`
- `~/.local/bin/agent-web-www`
- `~/.local/bin/agent-report-smoke`

Canonical publish root:

- filesystem: `/opt/agent-web/www`
- URL: `/www/`

Install or refresh runtime copies:

```bash
scripts/agent-web/install-agent-web-tools.sh
```

Validate:

```bash
bash -n scripts/agent-web/agent-report scripts/agent-web/agent-web-www scripts/agent-web/agent-report-smoke scripts/agent-web/install-agent-web-tools.sh
shellcheck scripts/agent-web/*.sh scripts/agent-web/agent-report scripts/agent-web/agent-web-www scripts/agent-web/agent-report-smoke
/opt/agent-web/bin/agent-web-www validate
```

Rules:

- Keep source here.
- Keep generated reports out of this repo.
- Keep evidence under `~/.AGENTS-temp/<repo>/`.
- Do not bulk-migrate old `/opt/agent-web/<lane>/` reports without a separate reviewed plan.
