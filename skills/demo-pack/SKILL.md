---
name: demo-pack
description: Build a demo pack in a cloud VM, with offline walkthrough pages plus captioned PNG, MP4 and GIF captures. Use when a project needs slides-free proof of a pipeline, built from committed recorded data.
---

# demo-pack

Turn a pipeline's recorded output into a demo anyone can open offline: static
pages, captioned screenshots, a short video and a GIF. Pattern taken from
`docs/demo/` in kcloud1/agentic-pentest-poc.

## Rules

1. **Source of truth is committed sample data.** Pages are built from files in
   git (for the pentest POC: `docs/sample`), never from a live run, so a rebuild
   gives the same result.
2. **Pages are static.** No scripts, no network, no external fonts. They must
   open from `file://` on a laptop with no internet.
3. **Never touch the live system while capturing.** Do not start, stop or scan
   the lab. Reuse the one VM and the existing tool logins. Do not reboot it.
4. **Captures are reproducible.** One `make` target rebuilds everything.
5. **Keep sizes sane.** Check the totals before committing (see Budget).

## Steps

1. **Prerequisites** (once per VM): Node 22, ffmpeg, Playwright with headless
   Chromium (`cd docs/demo && npm ci && npx playwright install chromium`).
   Pin the Playwright version in `package.json`. Do not reinstall Playwright if
   it is already on the VM.
2. **Build pages.** A small script (`walkthrough.py`) reads the sample data and
   writes one HTML file per step into `docs/demo/walkthrough/`, plus an index.
3. **Capture PNGs.** `record.js png` opens each page in headless Chromium:
   dark colour scheme, `deviceScaleFactor: 2`, a numbered caption on each shot.
   Wait for fonts and layout to settle before the shot.
4. **Record video.** `record.js video` uses Playwright `recordVideo` while
   stepping through the pages with pauses long enough to read (about 3 s per
   page). Convert the webm to MP4 with `ffmpeg -c:v libx264 -pix_fmt yuv420p`.
5. **Make the GIF** with a palette, not the default dither:
   `ffmpeg -i demo.mp4 -vf "fps=8,scale=960:-1:flags=lanczos,palettegen" p.png`
   then `paletteuse` (`-i demo.mp4 -i p.png -lavfi "fps=8,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse"`). fps 8 and width 960 keep it near 10 MB.
6. **Wire one target**, e.g. `make demo-pack`, that runs steps 2 to 5 in order,
   and a `make walkthrough` for pages only.
7. **Check** with `scripts/check.sh` (below), then open two or three PNGs by eye.
8. **Commit** the pages, PNGs, MP4 and GIF together with the README that says
   how to rebuild. Open one PR.

## Budget

| Artifact | Target |
|---|---|
| PNG set | under 5 MB total |
| MP4 | under 5 MB |
| GIF | under 12 MB (GitHub inline limit is higher, chat apps lower) |
| Any single page | under 5 MB |

## Check

Run `bash scripts/check.sh docs/demo`. It fails on: a page with `<script`,
`src`/`href` links to `http(s)://`, a missing or empty PNG, MP4 or GIF,
and a total over budget.

## Common mistakes

- Capturing before fonts load gives blank or shifted text. Wait for settle.
- A GIF made without `palettegen` is huge and banded.
- Rebuilding from a live run makes diffs noisy. Rebuild from sample data.
- Printing or committing secrets that appear in a terminal capture. Review shots.

## Cycle 3 additions

- Run `check.sh` before every commit; it exits non-zero on any failure.
- Terminal captures can show tokens or hostnames. Look at every PNG first.
- Reference implementation: `docs/demo/` in kcloud1/agentic-pentest-poc
  (`make demo-pack`, `make walkthrough`).
