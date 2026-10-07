const { chromium } = require("playwright");
const { pathToFileURL } = require("node:url");
const path = require("node:path");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.DOCGEN_BROWSER || "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  const url = pathToFileURL(path.resolve("runs/ui-verification/graph-preview/index.html")).href;
  for (const [name, width, height] of [["desktop", 1440, 900], ["mobile", 390, 844]]) {
    await page.setViewportSize({width, height});
    await page.goto(url);
    await page.selectOption("#capability", "delivery");
    await page.waitForFunction(() => network.getPositions().delivery !== undefined);
    await page.waitForTimeout(1000);
    await page.screenshot({path: `runs/ui-verification/${name}.png`, fullPage: true});
    const pixels = await page.evaluate(() => {
      const canvas = document.querySelector("canvas");
      const rgba = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
      let colored = 0;
      for (let i = 0; i < rgba.length; i += 4) if (rgba[i+3] > 0 && (rgba[i] < 220 || rgba[i+1] < 220 || rgba[i+2] < 220)) colored++;
      return colored;
    });
    assert(pixels > 300, `Blank canvas: ${pixels}; ${errors.join('; ')}`);
    const position = await page.evaluate(() => network.canvasToDOM(network.getPositions(["delivery"]).delivery));
    const bounds = await page.locator("#network").boundingBox();
    await page.mouse.click(bounds.x + position.x, bounds.y + position.y);
    await page.getByText("Conditions: Only while delivery remains enabled", {exact: true}).waitFor();
    await page.locator("aside details summary").first().click();
    assert(await page.locator("aside pre").innerText().then(t => t.includes("Attempts")));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.screenshot({path: `runs/ui-verification/${name}.png`, fullPage: true});
    await page.fill("#search", "no such entity");
    await page.locator("#empty:not([hidden])").waitFor();
    await page.click("#reset");
    assert(await page.locator("#empty").isHidden());
  }
  assert.deepEqual(errors, []);
  const diagramPath = path.resolve("runs/ui-verification/rendered/delivery-delivery.svg");
  if (require("node:fs").existsSync(diagramPath)) {
    await page.setViewportSize({width: 900, height: 600});
    await page.goto(pathToFileURL(diagramPath).href);
    assert(await page.locator("svg").count() > 0);
    await page.screenshot({path: "runs/ui-verification/diagram.png"});
  }
  await browser.close();
  console.log("Graph preview passed desktop/mobile interaction, layout and canvas checks.");
})().catch(error => { console.error(error); process.exit(1); });
