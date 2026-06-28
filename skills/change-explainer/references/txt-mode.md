# TXT Mode

Default TXT output is a terminal dashboard, not plain Markdown.

Use semantic glyphs:

- `🟢` pass
- `🟡` warning
- `⛔` boundary held or no-go gate
- `✗ -> ✓` changed state
- `↺` rollback
- `💥` blast radius
- `🔒` secret/safety

## Default Sections

Use these 3-5 sections for normal TXT/ANSI output:

1. `WHY THIS CHANGE MATTERS`
2. `WHAT CHANGED`
3. `EVIDENCE` plus `VALIDATION LEDGER`
4. `RISK / GATE`

Add the bigger panels only when Amit asks for `detail` or `big`.

In detail/big mode:

- add repo path when showing changed files
- add a `Change` column for code and AWS/resource facts
- make major actions visible with markers:
  - `❌ Deleted`
  - `❎ Added`
  - `👍🏽 Updated`
  - `🟢 Verified`
  - `🟡 Warning`
  - `⛔ Blocked`
- do not include a final `Run / Mode / Saved file` panel in the report; Codex
  chat should say that after generating the file

## Detail Pattern

```text
╭────────────────────────────────────────────────────────────╮
│ 🔥 WHY THIS CHANGE MATTERS                                 │
╰────────────────────────────────────────────────────────────╯

TRIGGER -> CHANGE -> EFFECT -> EVIDENCE -> GATE

┌─ Δ changed thing ─────────────────────────────────────────┐
│ ✗ before -> ✓ after                                      │
└───────────────────────────────────────────────────────────┘

●  path / file / resource
   └─ effect
      ├─▶ check .................................. ✅ result
      └─▶ boundary ............................... ⛔ held

┌─────┬────────────────────────────┬───────────────────────┐
│  ●  │ CHECK                      │ RESULT                │
└─────┴────────────────────────────┴───────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
↺ REVERSIBLE  ...
💥 BLAST       ...
⛔ PROD        ...
🔒 SECRETS     ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Rules

- Start with why it matters.
- Show direction with arrows.
- Keep each section answering one question.
- Prefer concise evidence paths over raw logs.
- Use color when Rich is available; save plain TXT too.
- Prefer the `.ansi` artifact as the one file to show Amit with `cat`.
- Add `--ascii` fallback only when strict ASCII is requested.

## Optional Tool Ideas

These are useful later, not required for MVP:

- `difftastic`: structural code-diff input for better "what changed logically".
- `delta`: colored raw diff sidecar when Amit asks for deeper diff view.
- `glow`: terminal preview for saved Markdown evidence if Markdown output is
  added later.
- `termaid` or `mermaid-ascii`: optional small terminal diagrams only when a
  flow is hard to explain with native Rich boxes.
- `revdiff`, `hunk`, `sigil`: optional interactive review loops; do not make
  them the default explainer path.

Do not render an "optional tools detected" section in normal reports. Amit wants
the report focused on the change, not the renderer/tooling.
