---
name: plan-decision-form
description: "Build a standalone offline Decision Studio (DSP) HTML form with proposed options preselected, explicit owner-opted-in review-by-exception, portable decision JSON and a Copy Agent Prompt handoff. Use for several consequential decisions, roadmap choices, skill preferences or tradeoffs. Use a short text question for trivial decisions."
---

# Decision Studio (portable)

Use **Decision Studio** as the human-facing name. Keep this existing skill ID
`plan-decision-form` and path for installed references; do not create a second
skill or depend on a running web server.

Decision Studio reviews and records choices. An interactive "grill me" interview
clarifies uncertain requirements **before** building the Studio, when useful;
it is not a replacement for confirmation, comparison, or JSON export.

## Workflow

1. Read the exact owning Issue/PR, existing decisions and current evidence.
   Recommend one option per question with brief facts and tradeoffs. For a
   trivial decision use text; otherwise render the requested HTML directly.
2. Prepare a **sanitized JSON specification** with 1–30 stable decisions.
   Each needs `id`, `title`, `choices`, `recommended`, and `rationale`.
   **Review by exception** is this owner's explicitly opted-in preference:
   use `confirmation_mode: owner_opt_in_default_agreed` and
   `owner_opt_in: true`. This means all recommendations start selected and
   **agreed**; the owner only changes exceptions. For an owner without an
   explicit opt-in, use `proposal_first` and `owner_opt_in: false`; selected
   recommendations remain unconfirmed. Never infer consent from a default.
3. Render one offline file using the existing stdlib renderer:

   ```bash
   python3 scripts/render_portable.py --spec decisions.json --out decision-studio.html
   ```

4. Give the owner the single portable `decision-studio.html` file. It runs
   locally (**file://**, no server): dark/light themes, recommended choices
   first, search, local resume where supported, **Export/Import JSON** and
   **Copy agent prompt** (with a selectable-text fallback). In opted-in mode,
   changing a selection keeps it agreed; unchecking makes it **pending**.
   Nothing is sent to a server or executed.
5. On return, validate the exported packet against the original spec:

   ```bash
   python3 scripts/render_portable.py --spec decisions.json --check-packet decision-packet.json
   ```

6. Summarize **accepted**, **proposed/pending**, and conflicts separately.
   Reconcile the exported packet with the existing Issue/PR/Spec and record
   choices durably. The packet and copied prompt record preferences, **not**
   GitHub merge, AWS, PROD, IAM, spending, secret or deployment authority.

## Example spec

```json
{
  "schema_version": "decision-packet/1",
  "source": "https://github.com/amitkarpe/agent-skills",
  "title": "Daily skill exposure",
  "confirmation_mode": "owner_opt_in_default_agreed",
  "owner_opt_in": true,
  "decisions": [
    {
      "id": "skill-profile",
      "title": "Which daily skill profile?",
      "choices": ["default", "no-aws"],
      "recommended": "default",
      "rationale": "Default is AWS-first; no-aws enables only core skills."
    }
  ]
}
```

The output packet preserves source, confirmation mode and opt-in, stable IDs,
recommendations, actual choices, `state`, `frozen` and export time. With the
recorded owner opt-in, unchanged recommendations export as `accepted`/`true`;
selecting another option remains agreed unless the owner unchecks it. Pending
items remain pending across selection changes, refresh and JSON import/export.
For `proposal_first`, acceptance still requires checking each selection.
Always validate the packet against its exact spec before using it.

Use only sanitized source facts, never credentials, tokens, private host details
or sensitive inventories. HTML, prompts and exported JSON can be forwarded;
check confidentiality before sharing. Copy Prompt is a handoff, not execution.

## Legacy compatibility (explicit only)

The older server-bound `scripts/plan_decision_form.py` remains in the same
skill for existing Agent Web/Agent Share consumers. It is **not** the default
and should not be invoked for portable forms. Do not start or install
`/opt/agent-web`, publish forms, or migrate old saved decisions automatically.
