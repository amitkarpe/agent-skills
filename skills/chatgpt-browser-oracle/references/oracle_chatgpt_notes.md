# Oracle ChatGPT Notes

Current local assumptions:

- Chrome user service: `oracle-chrome-amit.service`
- Chrome profile path: `/home/dev/.chrome-oracle-amit`
- Profile display name: `Amit_CHATGPT`
- DevTools endpoint: `127.0.0.1:9222`
- Disposable project:
  `https://chatgpt.com/g/g-p-6a154595feb881918c8184fdad6b832b/project`
- Project name: `Oracle Codex Tests`
- Control tab rule: tab 1 is the operator tab; press `Ctrl+1` before a run.
- Active runtime home:
  `/home/dev/.AGENTS-temp/chatgpt-browser-oracle/`
- Old notebook-local Oracle material belongs under:
  `/home/dev/.AGENTS-temp/codex/archive/`

Known behavior:

- Oracle CLI browser mode can return sandbox file links without leaving a clean
  visible project chat.
- Direct browser project submission creates normal project chats and is better
  for generated artifacts.
- Oracle CLI logs can show older compatibility labels such as
  `gpt-5.4-pro[browser]`; for Pro confirmation, trust live UI/DOM instead.
- For current Pro runs, useful proof can include visible composer text `Pro` and
  assistant message DOM slug `gpt-5-5-pro` when available.

Recovery checklist:

1. Check service: `systemctl --user is-active oracle-chrome-amit.service`.
2. Check DevTools: `curl -fsS http://127.0.0.1:9222/json/version`.
3. Focus control tab: `bash scripts/chatgpt_focus_control_tab.sh`.
4. If model selection is slow, rerun `chatgpt_ensure_model.js --select true`
   and inspect the saved JSON before submitting.

Validated artifact types on 2026-05-26:

- PDF, DOCX, PPTX from earlier browser runs.
- ZIP containing Python code.
- HTML with inline JavaScript.
- GIF image.
- XLSX through the project-browser path.

Not yet validated in this harness:

- standalone `.js` file download
- PNG/JPEG image download
- video/movie download

XLSX behavior:

- ChatGPT may render XLSX as a workbook preview card rather than a plain
  filename button.
- The download action can be an unlabeled icon button in the card header.

Strict validation rule:

- Validate the durable copy, not only the browser Downloads copy.
- Confirm exact filename when the prompt specified one.
- For zip-like files, check both `unzip -t` and required internal entries.
- For Office files, require the expected OOXML root file:
  - DOCX: `word/document.xml`
  - PPTX: `ppt/presentation.xml`
  - XLSX: `xl/workbook.xml`
- Record SHA-256 in download evidence and reject mismatched copied artifacts.
