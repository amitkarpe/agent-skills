#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

let CDP;
try {
  CDP = require('chrome-remote-interface');
} catch {
  CDP = require('/home/dev/.npm/_npx/e5c1cd02bea5357a/node_modules/chrome-remote-interface');
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function arg(name, fallback = '') {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const host = arg('host', process.env.CHATGPT_CDP_HOST || '127.0.0.1');
const port = Number(arg('port', process.env.CHATGPT_CDP_PORT || '9222'));
const projectUrl = arg('project-url', 'https://chatgpt.com/g/g-p-6a154595feb881918c8184fdad6b832b/project');
const promptFile = arg('prompt-file');
const outDir = arg('out-dir', process.cwd());

if (!promptFile) {
  console.error('Missing --prompt-file');
  process.exit(2);
}

async function getClient() {
  const targets = await CDP.List({ host, port });
  const target =
    targets.find((t) => t.type === 'page' && t.url.startsWith('https://chatgpt.com/')) ||
    targets.find((t) => t.type === 'page');
  if (!target) throw new Error(`No browser page found on ${host}:${port}`);
  const client = await CDP({ host, port, target });
  await client.Page.enable();
  await client.Runtime.enable();
  return client;
}

async function evalValue(Runtime, expression) {
  const res = await Runtime.evaluate({ expression, awaitPromise: true, returnByValue: true });
  if (res.exceptionDetails) throw new Error(res.exceptionDetails.text || 'Runtime.evaluate failed');
  return res.result.value;
}

async function main() {
  const prompt = fs.readFileSync(promptFile, 'utf8');
  fs.mkdirSync(outDir, { recursive: true });

  const client = await getClient();
  const { Page, Runtime, Input } = client;

  await Page.navigate({ url: projectUrl });
  await sleep(2500);

  let ready = null;
  for (let i = 0; i < 30; i += 1) {
    ready = await evalValue(Runtime, `
(() => {
  const el = document.querySelector('#prompt-textarea.ProseMirror, #prompt-textarea, [contenteditable="true"]');
  if (!el) return { ok: false, url: location.href, title: document.title };
  el.scrollIntoView({ block: 'center' });
  el.focus();
  return { ok: true, url: location.href, title: document.title, tag: el.tagName, id: el.id || '' };
})()
`);
    if (ready.ok) break;
    await sleep(1000);
  }
  if (!ready.ok) throw new Error(`Could not find ChatGPT prompt composer: ${JSON.stringify(ready)}`);

  await Input.insertText({ text: prompt });
  await sleep(400);
  await Input.dispatchKeyEvent({ type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await Input.dispatchKeyEvent({ type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });

  let chatUrl = '';
  for (let i = 0; i < 90; i += 1) {
    await sleep(1000);
    const current = await evalValue(Runtime, `location.href`);
    if (current.includes('/c/')) {
      chatUrl = current;
      break;
    }
  }
  if (!chatUrl) chatUrl = await evalValue(Runtime, `location.href`);

  fs.writeFileSync(path.join(outDir, 'chat-url.txt'), `${chatUrl}\n`);
  fs.writeFileSync(path.join(outDir, 'submit-proof.json'), `${JSON.stringify({
    ok: true,
    submittedAt: new Date().toISOString(),
    promptFile,
    chatUrl,
  }, null, 2)}\n`);
  console.log(JSON.stringify({ ok: true, chatUrl }, null, 2));
  await client.close();
}

main().catch((err) => {
  console.error(err.stack || err.message);
  process.exit(1);
});
