---
name: chatgpt-browser-oracle
description: Use Amit's authenticated ChatGPT browser session through the Oracle Chrome profile to submit prompts, select Instant/Thinking/Pro when needed, collect generated files, validate downloads, and return durable artifact paths. Use for ChatGPT Project runs, Oracle browser runs, Pro asks, generated PDF/DOCX/PPTX/XLSX/ZIP/HTML/image artifacts, or handing ChatGPT results to another Codex worker.
---

# ChatGPT Browser Oracle

Use this skill when the work requires Amit's logged-in ChatGPT browser session,
especially generated files or Pro/Thinking model runs that Codex cannot perform
through the normal local model.

## Defaults

- Default project URL:
  `https://chatgpt.com/g/g-p-6a154595feb881918c8184fdad6b832b/project`
- Default Chrome DevTools endpoint: `127.0.0.1:9222`
- Default browser service: `oracle-chrome-amit.service`
- Default durable output base: `~/.AGENTS-temp/chatgpt-browser-oracle`
- Use `instant` for smoke tests.
- Use `thinking` for medium non-Pro work.
- Use `pro` only for real high-value work.

## Rules

- Treat browser UI/DOM state as source of truth for selected model.
- Before any real `pro` run, prove the composer shows `Pro`; if it still shows
  `Extended`, stop before submitting.
- For generated files, prefer the project-browser path over plain Oracle CLI so
  the chat remains visible in the ChatGPT project.
- Save run evidence under `~/.AGENTS-temp/chatgpt-browser-oracle/out/<run-id>/`.
- Copy final manual-review artifacts to `/tmp/dell/`.
- Keep prompts in files, not chat history, when handing work between agents.

## Main Flow

```bash
base=/home/dev/.AGENTS-temp/chatgpt-browser-oracle
run="$base/out/run-$(date +%Y%m%d-%H%M%S)-<short-name>"
mkdir -p "$run" "$base/downloads" /tmp/dell

bash scripts/chatgpt_focus_control_tab.sh

node scripts/chatgpt_ensure_model.js \
  --mode instant \
  --project-url https://chatgpt.com/g/g-p-6a154595feb881918c8184fdad6b832b/project \
  --select true \
  --out "$run/model-before-run.json"

node scripts/chatgpt_submit_project_prompt.js \
  --project-url https://chatgpt.com/g/g-p-6a154595feb881918c8184fdad6b832b/project \
  --prompt-file "$run/prompt.txt" \
  --out-dir "$run"

node scripts/chatgpt_download_latest_file.js \
  --chat-url "$(cat "$run/chat-url.txt")" \
  --ext zip \
  --expect-name example \
  --out-dir "$base/downloads" \
  --copy-to /tmp/dell \
  --evidence-dir "$run"

bash scripts/validate_generated_file.sh \
  --file "$base/downloads/example.zip" \
  --expect zip \
  --expect-name example.zip \
  --require-entry hello_oracle.py
```

Before reporting success, run strict validation on the durable artifact path,
not only on `/home/dev/Downloads`.

## Script Notes

- `chatgpt_focus_control_tab.sh`: checks the Chrome service and DevTools, focuses
  Oracle Chrome, and presses `Ctrl+1`.
- `chatgpt_ensure_model.js`: inspects or selects `instant`, `thinking`, or `pro`
  and writes JSON proof.
- `chatgpt_submit_project_prompt.js`: opens the project, inserts the exact
  prompt file content, submits, and saves `chat-url.txt`.
- `chatgpt_download_latest_file.js`: clicks the newest matching download card or
  link, waits for the local download, copies it to the requested output paths,
  verifies SHA-256 equality across copies, and writes download evidence.
- `validate_generated_file.sh`: validates common generated artifacts with local
  tools. Prefer `--expect-name`, `--min-bytes`, and `--require-entry` when the
  prompt specified filenames or expected zip/Office contents.
- `oracle_run_browser.sh`: thin wrapper for plain Oracle browser CLI runs when a
  project-contained chat is not required.

Read `references/oracle_chatgpt_notes.md` only when environment assumptions or
failure recovery details are needed.
