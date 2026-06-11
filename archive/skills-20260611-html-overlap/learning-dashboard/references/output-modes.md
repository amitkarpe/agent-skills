# Output modes

## Single dashboard
Default. One self-contained HTML file. Best for most concepts, articles, code reviews, architecture explanations, release notes, and research summaries.

## Multi-page folder
Use only when the material is too large for one page or the user asks for a course/module format.

Required files:
- `index.html`
- `module-01.html`, `module-02.html`, etc.
- Optional local `style.css` only when a folder is explicitly requested.

## Compact dashboard
Use for quick learning. Keep to 5-7 sections:
- Hero
- 30-second view
- Concept map
- Workflow
- Decision guide
- Deep dive
- Quiz

## Codex behavior
When running inside a repository, write output under one of:
- `docs/learning/`
- `.codex/output/learning-dashboard/`
- user-specified path

Do not modify application code unless the user asks. Treat dashboard generation as documentation output.
