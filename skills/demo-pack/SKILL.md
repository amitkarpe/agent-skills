---
name: demo-pack
description: Build an offline demo pack from recorded data: static walkthrough pages plus captioned dark-mode PNGs, an MP4 and a GIF. Use when a project needs a demo that opens with no network and rebuilds the same every time.
---

# demo-pack

Turn recorded output into a demo anyone can open offline: static pages,
screenshots, a short video and a GIF.

## Rules

1. **Recorded data only.** Pages are built from files in git, never from a live
   run, so a rebuild gives the same result. Do not call live systems.
2. **Pages are static.** No scripts, no network, no external fonts or CSS.
3. **One command rebuilds everything** (`make demo-pack`).
4. **Keep sizes sane** (Budget below).
5. The owning project's own rules (VMs, logins, isolation) still apply.

## Layout

```
<demo>/steps.json    recorded data: [{"title": "...", "body": "<p>html</p>"}]
<demo>/walkthrough/  index.html, 01.html, 02.html ...
<demo>/png/          01.png ...
<demo>/video/        demo.mp4, demo.gif
```

## Steps

1. **Tools**: Node, ffmpeg, Playwright with headless Chromium. If
   `require('playwright')` fails and a preinstalled copy exists, set `NODE_PATH`
   to its `node_modules`; otherwise `npm i playwright` and
   `npx playwright install chromium` in the demo folder. Pin the version.
2. **Copy the templates** from `templates/` into the demo folder:
   `walkthrough.py` (pages from `steps.json`), `record.js` (PNG and video
   capture) and the `Makefile.snippet` targets. They are about 40 lines each.
3. **Pages**: `python3 walkthrough.py steps.json walkthrough`.
4. **PNGs**: `node record.js png walkthrough png` gives 2x dark-mode shots.
   The capture hides the `<nav>` so links stay out of the images.
5. **Video**: `node record.js video walkthrough video` records about 3 s per
   page. Playwright names the file randomly, so the script renames it to
   `demo.webm`. Then `ffmpeg -i demo.webm -c:v libx264 -pix_fmt yuv420p demo.mp4`.
6. **GIF** with a palette, not the default dither: `palettegen` then
   `paletteuse` at fps 8, width 960 (exact commands are in the snippet).
7. **Check**: `bash <skill-dir>/scripts/check.sh <demo>`, then open two or three
   PNGs by eye.
8. Commit pages, PNGs, MP4 and GIF with a README that says how to rebuild.

## Budget

| Artifact | Target |
|---|---|
| PNG set | under 5 MB total |
| MP4 | under 5 MB |
| GIF | under 12 MB |
| Any single page | under 5 MB |

## What check.sh covers

Fails on: no HTML pages, a `<script>`, a network link in `src`, `href`,
`action`, `poster`, `data`, CSS `@import` or `url()`, a page over 5 MB, a missing
or empty PNG, MP4 or GIF, and a total over budget. It does not validate media
formats or that nav links resolve; a non-empty file is enough for a demo pack.

## Common mistakes

- Shooting before fonts load gives shifted text; wait for `document.fonts.ready`.
- A GIF without `palettegen` is huge and banded.
- Terminal captures can show tokens or hostnames. Look at every PNG first.
