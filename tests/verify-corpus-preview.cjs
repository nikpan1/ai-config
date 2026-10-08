const { chromium } = require("playwright");
const { pathToFileURL } = require("node:url");
const path = require("node:path");
const assert = require("node:assert/strict");
const fs = require("node:fs");

(async () => {
  assert(process.argv[2], "Pass the corpus graph-preview/index.html path");
  const output = path.resolve("runs/corpus-ui-verification");
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.DOCGEN_BROWSER || "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    for (const [name, width, height] of [["desktop", 1440, 900], ["mobile", 390, 844]]) {
      await page.setViewportSize({ width, height });
      await page.goto(pathToFileURL(path.resolve(process.argv[2])).href);
      const choice = await page.evaluate(() => {
        const candidates = graph.entities.filter(e => e.type === "capability")
          .map(e => ({ entity: e, claims: graph.claims.filter(c => c.entity_ids.includes(e.id)) }))
          .sort((a, b) => a.claims.length - b.claims.length);
        for (const item of candidates) {
          for (const claim of item.claims) {
            for (const id of claim.evidence_ids) {
              const span = spans.get(evidence.get(id)?.span_id);
              if (span?.table_header_excerpt) return { id: item.entity.id, evidenceId: id, header: span.table_header_excerpt.split("\n")[0].trim() };
            }
          }
        }
        throw new Error("No capability with row-level table evidence");
      });
      await page.selectOption("#capability", choice.id);
      await page.waitForTimeout(1200);
      await page.evaluate(() => { network.stopSimulation(); network.fit({ animation: false }); });
      const position = await page.evaluate(id => network.canvasToDOM(network.getPositions([id])[id]), choice.id);
      const bounds = await page.locator("#network").boundingBox();
      await page.mouse.click(bounds.x + position.x, bounds.y + position.y);
      await page.locator("aside summary").filter({ hasText: choice.evidenceId }).first().click();
      assert((await page.locator("aside pre").allTextContents()).some(text => text.includes(choice.header)));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.evaluate(() => { window.scrollTo(0, 0); network.redraw(); });
      await page.waitForTimeout(250);
      const pixels = await page.evaluate(() => {
        const canvas = document.querySelector("canvas");
        const rgba = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
        let count = 0;
        for (let i = 0; i < rgba.length; i += 4) if (rgba[i + 3] && rgba[i] < 220) count++;
        return count;
      });
      assert(pixels > 300, "Blank corpus graph");
      await page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true });
    }
    assert.deepEqual(errors, []);
    console.log("Saved corpus graph preview passed desktop/mobile evidence, canvas and overflow checks.");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
