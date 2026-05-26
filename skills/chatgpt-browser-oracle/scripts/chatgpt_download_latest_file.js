#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

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
const chatUrl = arg('chat-url', '');
const ext = arg('ext', '').replace(/^\./, '').toLowerCase();
const expectName = arg('expect-name', '').toLowerCase();
const outDir = arg('out-dir', '/home/dev/.AGENTS-temp/chatgpt-browser-oracle/downloads');
const copyTo = arg('copy-to', '');
const evidenceDir = arg('evidence-dir', outDir);
const downloadsDir = arg('downloads-dir', path.join(process.env.HOME || '/home/dev', 'Downloads'));
const timeoutSec = Number(arg('timeout-sec', '240'));

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

function snapshotDownloads() {
  if (!fs.existsSync(downloadsDir)) return new Set();
  return new Set(fs.readdirSync(downloadsDir).map((x) => path.join(downloadsDir, x)));
}

function findDownloaded(before) {
  if (!fs.existsSync(downloadsDir)) return '';
  const files = fs.readdirSync(downloadsDir)
    .filter((name) => !name.endsWith('.crdownload') && !name.endsWith('.tmp'))
    .filter((name) => !ext || name.toLowerCase().endsWith(`.${ext}`))
    .filter((name) => !expectName || name.toLowerCase().includes(expectName))
    .map((name) => {
      const p = path.join(downloadsDir, name);
      const st = fs.statSync(p);
      return { p, mtimeMs: st.mtimeMs, size: st.size, isNew: !before.has(p) };
    })
    .filter((x) => x.size > 0)
    .sort((a, b) => (Number(b.isNew) - Number(a.isNew)) || (b.mtimeMs - a.mtimeMs));
  return files[0] ? files[0].p : '';
}

function acceptDownloadDialog() {
  try {
    process.env.DISPLAY = process.env.DISPLAY || ':0';
    process.env.XAUTHORITY = process.env.XAUTHORITY || path.join(process.env.HOME || '/home/dev', '.Xauthority');
    const listing = execFileSync('wmctrl', ['-l'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
    if (/Save File|Opening|Open with|Downloads?|All Files/i.test(listing)) {
      execFileSync('xdotool', ['key', 'Return'], { stdio: 'ignore' });
    }
  } catch {
    // GUI helpers are best-effort only.
  }
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(evidenceDir, { recursive: true });
  if (copyTo) fs.mkdirSync(copyTo, { recursive: true });

  const before = snapshotDownloads();
  const client = await getClient();
  const { Page, Runtime } = client;

  if (chatUrl) {
    await Page.navigate({ url: chatUrl });
    await sleep(4500);
  }

  let clicked = { ok: false, candidates: [] };
  for (let attempt = 0; attempt < 45; attempt += 1) {
    clicked = await evalValue(Runtime, `
(async () => {
  const ext = ${JSON.stringify(ext)};
  const expectName = ${JSON.stringify(expectName)};
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
    el.getAttribute('download'),
    el.getAttribute('href'),
    el.getAttribute('data-testid')
  ].filter(Boolean).join(' | '));
  const nodes = [...document.querySelectorAll('a,button,[role="button"]')]
    .filter(visible)
    .map((el) => ({ el, text: label(el) }))
    .filter((x) => {
      const t = x.text.toLowerCase();
      const extOk = !ext || t.includes('.' + ext) || t.includes(ext);
      const nameOk = !expectName || t.includes(expectName);
      return (extOk && nameOk) || (t.includes('download') && extOk);
    });
  const picked = nodes.at(-1);
  if (!picked) {
    const card = [...document.querySelectorAll('div')]
      .filter(visible)
      .filter((el) => {
        const t = norm(el.innerText).toLowerCase();
        return expectName && t.includes(expectName) && (!ext || t.includes(ext));
      })
      .sort((a, b) => {
        const ar = a.getBoundingClientRect();
        const br = b.getBoundingClientRect();
        return (ar.width * ar.height) - (br.width * br.height);
      })[0];
    if (card) {
      const buttons = [...card.querySelectorAll('button,[role="button"]')].filter(visible);
      const iconButton = buttons.find((button) => !norm(button.innerText)) || buttons[0];
      if (iconButton) {
        iconButton.scrollIntoView({ block: 'center', inline: 'center' });
        await new Promise((resolve) => setTimeout(resolve, 200));
        iconButton.click();
        return { ok: true, text: 'file-card-icon-button', cardText: norm(card.innerText).slice(0, 200) };
      }
    }
    return {
      ok: false,
      candidates: [...document.querySelectorAll('a,button,[role="button"]')]
        .filter(visible)
        .map((el) => label(el))
        .filter(Boolean)
        .slice(-80)
    };
  }
  picked.el.scrollIntoView({ block: 'center', inline: 'center' });
  await new Promise((resolve) => setTimeout(resolve, 200));
  picked.el.click();
  return { ok: true, text: picked.text };
})()
`);
    if (clicked.ok) break;
    await sleep(1000);
  }
  fs.writeFileSync(path.join(evidenceDir, 'download-click.json'), `${JSON.stringify(clicked, null, 2)}\n`);

  if (clicked.ok && /download/i.test(clicked.text || '')) {
    await sleep(1200);
    const saveClicked = await evalValue(Runtime, `
(async () => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const buttons = [...document.querySelectorAll('button,[role="button"]')]
    .filter((el) => {
      const r = el.getBoundingClientRect();
      const st = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && st.display !== 'none' && st.visibility !== 'hidden';
    });
  const el = buttons.find((button) => norm(button.innerText || button.getAttribute('aria-label') || '') === 'Save');
  if (!el) return { ok: false };
  el.scrollIntoView({ block: 'center', inline: 'center' });
  await new Promise((resolve) => setTimeout(resolve, 150));
  el.click();
  return { ok: true, text: norm(el.innerText || el.getAttribute('aria-label') || '') };
})()
`);
    fs.writeFileSync(path.join(evidenceDir, 'download-save-click.json'), `${JSON.stringify(saveClicked, null, 2)}\n`);
  }

  let downloaded = '';
  for (let i = 0; i < timeoutSec; i += 1) {
    acceptDownloadDialog();
    downloaded = findDownloaded(before);
    if (downloaded) break;
    await sleep(1000);
  }

  await client.close();
  if (!downloaded) {
    throw new Error(`No matching download found in ${downloadsDir}; clicked=${JSON.stringify(clicked)}`);
  }

  const finalName = path.basename(downloaded);
  const durable = path.join(outDir, finalName);
  fs.copyFileSync(downloaded, durable);
  let copied = '';
  if (copyTo) {
    copied = path.join(copyTo, finalName);
    fs.copyFileSync(downloaded, copied);
  }
  const proof = { ok: true, clicked, downloaded, durable, copied };
  const downloadedHash = execFileSync('sha256sum', [downloaded], { encoding: 'utf8' }).split(/\s+/)[0];
  const durableHash = execFileSync('sha256sum', [durable], { encoding: 'utf8' }).split(/\s+/)[0];
  if (downloadedHash !== durableHash) {
    throw new Error(`Copied durable file hash mismatch: ${downloadedHash} != ${durableHash}`);
  }
  proof.sha256 = durableHash;
  if (copied) {
    const copiedHash = execFileSync('sha256sum', [copied], { encoding: 'utf8' }).split(/\s+/)[0];
    if (copiedHash !== durableHash) {
      throw new Error(`Copied review file hash mismatch: ${copiedHash} != ${durableHash}`);
    }
    proof.copiedSha256 = copiedHash;
  }
  fs.writeFileSync(path.join(evidenceDir, 'download-proof.json'), `${JSON.stringify(proof, null, 2)}\n`);
  console.log(JSON.stringify(proof, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message);
  process.exit(1);
});
