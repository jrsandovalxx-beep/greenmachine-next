// Morning wake: load the deployed app and wait until the board renders so the
// first real user of the day hits a warm cache (D-139/D-140/D-141). Plain
// playwright-core + system chromium; no repo code imported.
//
// D-141: marker waits must poll the /~/+/ child frame. Streamlit renders the
// app inside that frame (the top page is a management shell), so page-level
// text= selectors can never match and the job hung to its 30-min timeout.

import { chromium } from "playwright-core";

const APP_URL = "https://greenmachine.streamlit.app/";
const ATTEMPTS = 3;
const LOAD_TIMEOUT_MS = 120_000;
const BOARD_TIMEOUT_MS = 300_000; // per attempt; 3 attempts fit the 30-min job budget
const POLL_MS = 5_000;

// The board is considered loaded when any of these texts is visible: a normal
// board ("The shortlist"), an empty board, or the schedule-fetch failure banner
// (still a completed run — the caches are warm, which is the point).
const BOARD_MARKERS = [
  "text=The shortlist",
  "text=No batter grades",
  "text=schedule could not be fetched",
];

function appFrame(page) {
  return page.frames().find((f) => f.url().includes("/~/+/"));
}

async function boardRendered(page) {
  const deadline = Date.now() + BOARD_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const app = appFrame(page);
    if (app) {
      for (const marker of BOARD_MARKERS) {
        try {
          const el = await app.$(marker);
          if (el && (await el.isVisible())) return marker;
        } catch {
          // frame navigated mid-check; next poll re-resolves it
        }
      }
    }
    await page.waitForTimeout(POLL_MS);
  }
  return null;
}

for (let attempt = 1; attempt <= ATTEMPTS; attempt += 1) {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || "/usr/bin/chromium",
    args: ["--no-sandbox"],
  });
  try {
    const page = await browser.newPage();
    await page.goto(APP_URL, {
      waitUntil: "domcontentloaded",
      timeout: LOAD_TIMEOUT_MS,
    });
    const marker = await boardRendered(page);
    if (marker) {
      console.log(`board rendered on attempt ${attempt} (marker: ${marker})`);
      process.exit(0);
    }
    console.log(`attempt ${attempt}: board did not render in time`);
  } catch (error) {
    console.log(`attempt ${attempt} failed: ${error}`);
  } finally {
    await browser.close();
  }
}

console.error(`board never rendered after ${ATTEMPTS} attempts`);
process.exit(1);
