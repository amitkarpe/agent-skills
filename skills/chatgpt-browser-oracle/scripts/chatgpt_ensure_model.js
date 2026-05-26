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
const mode = arg('mode', 'inspect').toLowerCase();
const select = /^(1|true|yes)$/i.test(arg('select', 'false'));
const projectUrl = arg('project-url', '');
const outPath = arg('out', '');

const modelNeedles = {
  instant: ['Instant'],
  thinking: ['Thinking'],
  pro: ['Pro'],
};

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

async function openModelMenu(Input, Runtime) {
  await Runtime.evaluate({ expression: 'document.body.focus()', awaitPromise: true });
  await Input.dispatchKeyEvent({ type: 'keyDown', key: 'Control', code: 'ControlLeft', windowsVirtualKeyCode: 17, modifiers: 2 });
  await Input.dispatchKeyEvent({ type: 'keyDown', key: 'Shift', code: 'ShiftLeft', windowsVirtualKeyCode: 16, modifiers: 10 });
  await Input.dispatchKeyEvent({ type: 'keyDown', key: 'M', code: 'KeyM', windowsVirtualKeyCode: 77, modifiers: 10 });
  await Input.dispatchKeyEvent({ type: 'keyUp', key: 'M', code: 'KeyM', windowsVirtualKeyCode: 77, modifiers: 10 });
  await Input.dispatchKeyEvent({ type: 'keyUp', key: 'Shift', code: 'ShiftLeft', windowsVirtualKeyCode: 16, modifiers: 2 });
  await Input.dispatchKeyEvent({ type: 'keyUp', key: 'Control', code: 'ControlLeft', windowsVirtualKeyCode: 17, modifiers: 0 });
}

async function state(Runtime) {
  return evalValue(Runtime, `
(() => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && st.display !== 'none' && st.visibility !== 'hidden';
  };
  const label = (el) => norm([
    el.innerText,
    el.getAttribute('aria-label'),
    el.getAttribute('title'),
    el.getAttribute('data-testid')
  ].filter(Boolean).join(' | '));
  const controls = [...document.querySelectorAll('button,[role="button"],[role="menuitemradio"],[data-testid]')]
    .filter(visible)
    .map((el) => {
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        role: el.getAttribute('role') || '',
        testid: el.getAttribute('data-testid') || '',
        text: label(el),
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    });
  const composerModels = controls.filter((b) =>
    b.tag === 'BUTTON' &&
    /^(Pro|Extended|Instant|Thinking)/.test(b.text) &&
    b.y > Math.floor(window.innerHeight * 0.65)
  );
  const messageSlugs = [...document.querySelectorAll('[data-message-model-slug]')]
    .map((el) => el.getAttribute('data-message-model-slug'))
    .filter(Boolean);
  return {
    title: document.title,
    url: location.href,
    composerModel: composerModels.at(-1) || null,
    latestMessageModelSlug: messageSlugs.at(-1) || null,
    modelItems: controls.filter((b) =>
      b.testid.includes('model-switcher') ||
      ['Instant', 'Thinking', 'Pro'].includes(b.text) ||
      b.text.includes('Thinking') ||
      b.text.includes('Extended')
    ),
    bodyTail: norm(document.body.innerText).slice(-900),
  };
})()
`);
}

async function clickModel(Runtime, wanted) {
  return evalValue(Runtime, `
(async () => {
  const wanted = ${JSON.stringify(wanted)};
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && st.display !== 'none' && st.visibility !== 'hidden';
  };
  const label = (el) => norm([
    el.innerText,
    el.getAttribute('aria-label'),
    el.getAttribute('title'),
    el.getAttribute('data-testid')
  ].filter(Boolean).join(' | '));
  const candidates = [...document.querySelectorAll('[role="menuitemradio"],button,[role="button"],div,span')]
    .filter(visible)
    .filter((el) => {
      const text = label(el);
      if (wanted === 'Pro') return text === 'Pro' || text.includes('gpt-5-5-pro');
      return text === wanted || text.startsWith(wanted);
    });
  const el = candidates.sort((a, b) => {
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    return (ar.width * ar.height) - (br.width * br.height);
  })[0];
  if (!el) return { ok: false, wanted, candidates: candidates.length };
  el.scrollIntoView({ block: 'center', inline: 'center' });
  await new Promise((resolve) => setTimeout(resolve, 150));
  el.click();
  return { ok: true, wanted, text: label(el), candidates: candidates.length };
})()
`);
}

async function main() {
  const client = await getClient();
  const { Page, Runtime, Input } = client;
  const proof = { requestedMode: mode, selected: false, clicked: null, before: null, after: null, pass: false };

  if (projectUrl) {
    await Page.navigate({ url: projectUrl });
    await sleep(3500);
  }

  proof.before = await state(Runtime);

  if (select && mode !== 'inspect') {
    const wanted = (modelNeedles[mode] || [mode])[0];
    for (let attempt = 1; attempt <= 2; attempt += 1) {
      await openModelMenu(Input, Runtime);
      await sleep(1200);
      proof.clicked = await clickModel(Runtime, wanted);
      if (proof.clicked.ok) break;
      await sleep(800);
    }
    await sleep(2500);
    proof.selected = Boolean(proof.clicked && proof.clicked.ok);
  }

  proof.after = await state(Runtime);
  const visible = `${proof.after.composerModel ? proof.after.composerModel.text : ''} ${proof.after.bodyTail || ''}`;
  if (mode === 'inspect') proof.pass = true;
  else if (mode === 'pro') proof.pass = /\bPro\b/.test(visible) && !/\bExtended\b/.test(proof.after.composerModel ? proof.after.composerModel.text : '');
  else if (mode === 'thinking') proof.pass = /\bThinking\b/.test(visible);
  else if (mode === 'instant') proof.pass = /\bInstant\b/.test(visible);
  else proof.pass = true;

  const text = JSON.stringify(proof, null, 2);
  if (outPath) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, `${text}\n`);
  }
  console.log(text);
  await client.close();
  if (!proof.pass) process.exit(3);
}

main().catch((err) => {
  console.error(err.stack || err.message);
  process.exit(1);
});
