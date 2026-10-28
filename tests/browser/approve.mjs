// Drives the real approval page in Chromium with a CDP virtual authenticator.
// Usage: BASE_URL=... TOKEN=... QUOTE_ID=... node tests/browser/approve.mjs
// Proves protocol behaviour in a browser; not evidence of a physical PIN device (T22).
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const { BASE_URL, TOKEN, QUOTE_ID } = process.env;
const browser = await chromium.launch();
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('WebAuthn.enable');
  await cdp.send('WebAuthn.addVirtualAuthenticator', { options: {
    protocol: 'ctap2', transport: 'internal', hasResidentKey: true,
    hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true } });

  await page.goto(`${BASE_URL}/dev/login?token=${encodeURIComponent(TOKEN)}`);
  await page.goto(`${BASE_URL}/approve/quote/${QUOTE_ID}`);
  const text = await page.textContent('main');
  if (process.env.SCREENSHOT) await page.screenshot({ path: process.env.SCREENSHOT, fullPage: true });
  const status = page.locator('#msg');

  await page.getByRole('button', { name: 'Set up a passkey' }).click();
  await status.filter({ hasText: 'Passkey created' }).waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: 'Approve with passkey' }).click();
  await status.filter({ hasText: 'Approved' }).waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: 'Place order' }).click();
  await status.filter({ hasText: 'created' }).waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: 'Complete simulated payment step' }).click();
  await page.waitForURL(/\/orders\//, { timeout: 15000 });
  if (process.env.SCREENSHOT) await page.screenshot({ path: process.env.SCREENSHOT.replace('.png', '-status.png'), fullPage: true });
  const heading = await page.textContent('h1');
  console.log(JSON.stringify({ ok: true, heading, approvalPageText: text,
    orderUrl: page.url() }));
} catch (err) {
  console.log(JSON.stringify({ ok: false, error: String(err) }));
  process.exitCode = 1;
} finally {
  await browser.close();
}
