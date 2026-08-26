/**
 * D-136 (PO): the morning wake. Opens the deployed app in a headless
 * browser and waits until the board actually renders — a sleeping
 * Streamlit app first answers with its wake screen, and a cold start plus
 * a fresh-anchor board build can take several minutes, so the page is
 * given long waits and a few reloads before the job gives up loud.
 *
 * Success = the Sluggers surface rendered (the shortlist caption, or the
 * honest "no A/S batters" info, or the schedule-failure warning — all
 * three mean the app ran a real board build end to end).
 */
import { chromium } from "playwright-core";

const APP_URL = "https://greenmachine.streamlit.app/";
const ATTEMPTS = 3;
const LOAD_TIMEOUT_MS = 120_000;
const BOARD_TIMEOUT_MS = 480_000;

const BOARD_MARKERS = [
  "text=The shortlist",
  "text=No batter grades",
  "text=schedule could not be fetched",
];

async function boardRendered(page) {
  for (const marker of BOARD_MARKERS) {
    const found = await page
      .waitForSelector(marker, { timeout: BOARD_TIMEOUT_MS })
      .then(() => true)
      .catch(() => false);
    if (found) return marker;
  }
  return null;
}

for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    console.log(`attempt ${attempt}/${ATTEMPTS}: opening ${APP_URL}`);
    await page.goto(APP_URL, { timeout: LOAD_TIMEOUT_MS, waitUntil: "domcontentloaded" });
    const marker = await boardRendered(page);
    if (marker) {
      console.log(`board rendered (${marker}) — the morning build is warm`);
      process.exit(0);
    }
    console.log("no board marker yet — the app may still be waking; retrying");
  } catch (error) {
    console.log(`attempt ${attempt} failed: ${error}`);
  } finally {
    await browser.close();
  }
}

console.error(`the board did not render after ${ATTEMPTS} attempts`);
process.exit(1);
