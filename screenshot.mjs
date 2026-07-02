// Usage: node screenshot.mjs <url> [label] [--width=1440] [--mobile]
// Saves full-page screenshots to "./temporary screenshots/screenshot-N[-label].png"
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const root = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2).filter(a => !a.startsWith('--'));
const flags = process.argv.slice(2).filter(a => a.startsWith('--'));
const url = args[0];
if (!url) { console.error('Usage: node screenshot.mjs <url> [label] [--width=1440] [--mobile]'); process.exit(1); }
const label = args[1] ? `-${args[1]}` : '';
const mobile = flags.includes('--mobile');
const widthFlag = flags.find(f => f.startsWith('--width='));
const width = widthFlag ? parseInt(widthFlag.split('=')[1], 10) : (mobile ? 390 : 1440);
const height = mobile ? 844 : 900;

// Find newest cached chrome-headless-shell
const shellRoot = path.join(os.homedir(), '.cache/puppeteer/chrome-headless-shell');
const versions = fs.readdirSync(shellRoot).sort((a, b) =>
  b.localeCompare(a, undefined, { numeric: true }));
const dir = path.join(shellRoot, versions[0]);
const bin = fs.readdirSync(dir, { recursive: true })
  .map(String).find(f => f.endsWith('/chrome-headless-shell'));
const executablePath = path.join(dir, bin);

const outDir = path.join(root, 'temporary screenshots');
fs.mkdirSync(outDir, { recursive: true });
let n = 1;
while (fs.existsSync(path.join(outDir, `screenshot-${n}${label}.png`)) ||
       fs.readdirSync(outDir).some(f => f.startsWith(`screenshot-${n}-`) || f === `screenshot-${n}.png`)) n++;
const outPath = path.join(outDir, `screenshot-${n}${label}.png`);

const browser = await puppeteer.launch({ executablePath, headless: true });
const page = await browser.newPage();
await page.setViewport({ width, height, deviceScaleFactor: 1, isMobile: mobile, hasTouch: mobile });
await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise(r => setTimeout(r, 700)); // let fonts/animations settle
// scroll through the page so scroll-triggered reveals fire, then return to top
await page.evaluate(async () => {
  await new Promise(res => {
    let y = 0;
    const t = setInterval(() => {
      y += 600; scrollTo(0, y);
      if (y >= document.documentElement.scrollHeight - innerHeight) { clearInterval(t); res(); }
    }, 90);
  });
});
await new Promise(r => setTimeout(r, 900));
await page.evaluate(() => scrollTo(0, 0));
await new Promise(r => setTimeout(r, 400));
await page.screenshot({ path: outPath, fullPage: true });
await browser.close();
console.log(outPath);
