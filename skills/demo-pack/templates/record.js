// Capture pages with Playwright. Usage: node record.js png|video <walkthrough_dir> <out_dir>
// Needs: require('playwright'); if it fails, set NODE_PATH to the folder that holds it.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [mode, dir, out] = process.argv.slice(2);
const pages = fs.readdirSync(dir).filter(f => /^\d+\.html$/.test(f)).sort();
const HIDE_NAV = 'nav{display:none!important}';       // keeps nav links out of the shots
const url = f => 'file://' + path.resolve(dir, f);

(async () => {
  const browser = await chromium.launch();
  fs.mkdirSync(out, { recursive: true });
  if (mode === 'png') {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 },
      deviceScaleFactor: 2, colorScheme: 'dark' });
    const page = await ctx.newPage();
    for (const [i, f] of pages.entries()) {
      await page.goto(url(f)); await page.addStyleTag({ content: HIDE_NAV });
      await page.evaluate(() => document.fonts.ready);           // settle before the shot
      await page.screenshot({ path: path.join(out, `${String(i + 1).padStart(2, '0')}.png`) });
    }
  } else {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, colorScheme: 'dark',
      recordVideo: { dir: out, size: { width: 1280, height: 720 } } });
    const page = await ctx.newPage();
    for (const f of pages) {
      await page.goto(url(f)); await page.addStyleTag({ content: HIDE_NAV });
      await page.waitForTimeout(3000);                           // time to read
    }
    const tmp = await page.video().path();
    await ctx.close();                                           // flushes the video file
    fs.renameSync(tmp, path.join(out, 'demo.webm'));             // Playwright names it randomly
  }
  await browser.close();
})();
