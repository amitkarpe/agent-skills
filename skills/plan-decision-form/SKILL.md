---
name: plan-decision-form
description: 'Create a dark local Agent Web decision form that records Amit''s selections in one canonical decision.json. Use when Amit explicitly asks for a decision or HTML form, or after Amit approves HTML for more than five questions or complex evidence review. Default one to five questions to text/TUI.'
---

# Plan Decision Form

Create a small decision form using the existing Agent Web form assets and
submit contract. Read `/opt/agent-web/AGENTS.md` before publishing.
The canonical human trigger is `decision form: <file-or-topic>`.

## Workflow

1. Choose the interface before rendering:
   - An explicit Amit request for a decision form or HTML is direct approval.
   - Otherwise, use TEXT/TUI for one to five questions.
   - For more than five questions, ask Amit before creating HTML.
   - For one to five questions with diagrams, long evidence, or comparisons,
     also ask Amit before creating HTML.
   - Prefer TEXT/TUI because it is faster and uses fewer tokens. HTML is
     optional decision support, not the default.
2. Derive a mandatory path-safe repository name and plan ID. Use lowercase
   letters, digits, dots, dashes, or underscores; start with a letter or digit.
3. Write a JSON form spec under `~/.AGENTS-temp/<repo>/`. Keep only the
   blocking questions, recommended defaults, optional collapsed evidence, and
   no secrets. Supported question types are `radio`, `checkbox`, `select`,
   `text`, and `textarea`.
4. Render the form:

   ```bash
   python3 scripts/plan_decision_form.py render \
     --repo-name <repo-name> \
     --plan-id <plan-id> \
     --spec <form-spec.json>
   ```

5. Report the URL exactly as
   `http://home/amit/plans/<repo-name>/<plan-id>/` and validate it with
   `curl -fsSI`. Do not report success before the URL responds.
6. Wait for Amit to say `submitted`. Then validate and read only the computed
   canonical decision path:

   ```bash
   python3 scripts/plan_decision_form.py validate-decision \
     --repo-name <repo-name> \
     --plan-id <plan-id>
   ```

7. Treat the decision as input only. Re-check the owning repo SPEC, mutation
   approval, and safety gates before acting.

## Form spec

Use this shape:

```json
{
  "title": "Short decision title",
  "goal": "What Amit needs to decide. Do not enter secrets.",
  "decision_needed": "One bounded decision.",
  "owner_label": "Originating agent",
  "evidence": ["Optional concise proof."],
  "sections": [
    {
      "title": "Direction",
      "questions": [
        {
          "id": "next_action",
          "label": "What should happen next?",
          "type": "radio",
          "required": true,
          "default": "review",
          "options": [
            {"value": "review", "label": "Review only", "detail": "Recommended."},
            {"value": "execute", "label": "Prepare execution"}
          ]
        }
      ]
    }
  ]
}
```

The shared renderer adds the final free-text instruction unless
`allow_custom_direction` is false. Never ask for credentials, tokens, keys,
cookies, authentication data, or arbitrary filesystem destinations.

The renderer refuses unsafe identifiers, remote assets, secret-like fields,
and conflicting existing pages. Test output roots are accepted only under
`~/.AGENTS-temp`; the normal output path is fixed by the Agent Web contract.
