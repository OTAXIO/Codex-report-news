#!/usr/bin/env node
// Headless, isolated Skland capture driver for DSH (see docs/DSH_PROMPT.md 森空岛节).
//
// Opens a Skland official list/article page in a BRAND-NEW temporary profile using
// the project-local Playwright Chromium, lets React render, scrolls a few times,
// then runs skland_capture.js in the page and writes the returned JSON verbatim.
//
// It does not log in, read or write cookies, replay or forge API requests, and it
// never touches the user's Chrome profile. Usage:
//   node skland_browser_capture.mjs <url> <out.json>
import { createRequire } from 'node:module';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ROOT = path.dirname(fileURLToPath(import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(ROOT, '.cache', 'playwright');

const pwEntry = require.resolve('playwright', { paths: [require.resolve('multiplane')] });
const { chromium } = require(pwEntry);

const url = process.argv[2];
const out = process.argv[3];
if (!url || !out) {
  console.error('usage: node skland_browser_capture.mjs <url> <out.json>');
  process.exit(2);
}

const captureScript = await readFile(path.join(ROOT, 'skland_capture.js'), 'utf8');
const profile = await mkdtemp(path.join(os.tmpdir(), 'dsh-skland-profile-'));
const context = await chromium.launchPersistentContext(profile, {
  headless: true,
  viewport: { width: 1440, height: 1200 },
  args: ['--no-first-run', '--no-default-browser-check'],
});
try {
  const page = context.pages()[0] ?? (await context.newPage());
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  const isArticle = /\/article\?/.test(url);
  const linkCount = () =>
    page.evaluate(() => new Set([...document.querySelectorAll('a[href*="/article?id="]')].map((a) => a.href)).size);
  if (isArticle) {
    await page.waitForTimeout(6000);
  } else {
    // Wait for React to render the list, then scroll until no new posts appear.
    await page.waitForSelector('a[href*="/article?id="]', { timeout: 45000 }).catch(() => {});
    let previous = -1;
    for (let i = 0; i < 12; i += 1) {
      await page.mouse.wheel(0, 1800);
      await page.waitForTimeout(1500);
      const current = await linkCount();
      if (current === previous && i >= 2) break;
      previous = current;
    }
  }
  await page.waitForTimeout(1500); // let React settle before reading fiber props
  const data = await page.evaluate(captureScript);
  if (!data || !Array.isArray(data.rows)) throw new Error('capture returned no rows array');
  await writeFile(out, JSON.stringify(data, null, 2), 'utf8');
  console.log(JSON.stringify({ page: data.page, captured_at: data.captured_at, hours: data.hours, rows: data.rows.length }));
} finally {
  await context.close();
}
