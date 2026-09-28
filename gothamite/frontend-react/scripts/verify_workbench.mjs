import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(frontend, "..");
const artifacts = resolve(root, "verification");
await mkdir(artifacts, { recursive: true });
const temporary = await mkdtemp(join(tmpdir(), "gothamite-e2e-"));
const url = "http://127.0.0.1:8043";
const python =
  process.platform === "win32"
    ? resolve(root, ".venv/Scripts/python.exe")
    : resolve(root, ".venv/bin/python");
const server = spawn(python, ["scripts/run_workbench.py"], {
  cwd: root,
  windowsHide: true,
  env: {
    ...process.env,
    PYTHONIOENCODING: "utf-8",
    GOTHAMITE_PORT: "8043",
    GOTHAMITE_DB_PATH: join(temporary, "test.db"),
    GOTHAMITE_ORIGINS: url,
  },
});
let serverLog = "";
server.stderr.on("data", (b) => {
  serverLog += b.toString();
});
server.stdout.on("data", (b) => {
  serverLog += b.toString();
});
let browser;
const errors = [];
const results = [];
async function check(name, run) {
  await run();
  results.push(name);
  console.log(`PASS ${name}`);
}
try {
  for (let i = 0; i < 60; i++) {
    try {
      if ((await fetch(url + "/health")).ok) break;
    } catch {
      /* startup */
    }
    if (server.exitCode !== null)
      throw new Error("Backend exited: " + serverLog);
    if (i === 59)
      throw new Error("Backend did not become healthy: " + serverLog);
    await new Promise((r) => setTimeout(r, 250));
  }
  browser = await chromium.launch({
    channel: process.env.GOTHAMITE_BROWSER || "msedge",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1060 },
    reducedMotion: "reduce",
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await check("Command center and source labeling", async () => {
    await page.goto(url, { waitUntil: "networkidle" });
    await page
      .getByRole("heading", { name: "Command center", exact: true })
      .waitFor();
    assert.equal(await page.locator(".wb-table tbody tr").count(), 4);
    assert.match(
      await page.locator(".wb-environment").innerText(),
      /SYNTHETIC/,
    );
    await page
      .getByRole("link", { name: /REFERENCE IOC 203.0.113.42/ })
      .waitFor();
    assert.deepEqual(
      await page.locator(".wb-pipeline > span").allTextContents(),
      [
        "01Collect→",
        "02Enrich→",
        "03Correlate→",
        "04Analyze→",
        "05Prioritize→",
        "06Investigate→",
        "07Respond→",
        "08Learn",
      ],
    );
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: join(artifacts, "command-center.png"),
      fullPage: true,
    });
  });
  await check("Global search to IOC profile to related incident", async () => {
    await page
      .getByRole("textbox", { name: "Global search", exact: true })
      .fill("203.0.113.42");
    await page
      .getByRole("textbox", { name: "Global search", exact: true })
      .press("Enter");
    await page.getByRole("link", { name: "203.0.113.42 IP-001" }).click();
    await page
      .getByRole("heading", { name: "203.0.113.42", exact: true })
      .waitFor();
    assert.match(await page.locator(".wb-metadata").innerText(), /TEST-NET-3/);
    await page.locator(".wb-evidence-row").first().click();
    await page.locator(".wb-hash").waitFor();
    await page.getByRole("button", { name: "Close evidence" }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: join(artifacts, "ioc-profile.png"),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Relationship graph", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Evidence relationship graph" })
      .waitFor();
    await page
      .getByRole("button", {
        name: "Select Finance gateway beaconing",
        exact: true,
      })
      .click();
    await page
      .getByRole("link", { name: "Open investigation", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Finance gateway beaconing", exact: true })
      .waitFor();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: join(artifacts, "investigation.png"),
      fullPage: true,
    });
  });
  await check("Evidence drawer and integrity hash", async () => {
    await page.locator(".wb-evidence-row").first().click();
    await page.locator(".wb-hash").waitFor();
    assert.match(await page.locator(".wb-hash").innerText(), /^[a-f0-9]{64}$/);
    await page.getByRole("button", { name: "Close evidence" }).click();
  });
  await check("Graph evidence navigation and scope", async () => {
    await page.getByRole("button", { name: "Graph", exact: true }).click();
    await page.locator(".wb-graph-node").first().waitFor();
    // Collapsed presentation deliberately shows the eight-step primary chain.
    assert.equal(await page.locator(".wb-graph-node").count(), 8);
    assert.ok((await page.locator(".wb-graph-edge").count()) <= 8);
    assert.equal(
      await page.locator(".wb-relationship-groups details[open]").count(),
      0,
    );
    await page.getByRole("button", { name: "Full graph", exact: true }).click();
    assert.ok((await page.locator(".wb-graph-node").count()) >= 10);
    const fullLinks = await page.locator(".wb-graph-edge").count();
    assert.ok(fullLinks > 8);
    // Readability: no relationship line may pass behind an unrelated entity.
    const crossings = await page.evaluate(() => {
      const boxes = [...document.querySelectorAll("g[data-node]")].map((g) => {
        const r = g.querySelector("rect").getBBox();
        const [, x, y] = g
          .getAttribute("transform")
          .match(/translate\(([-\d.]+) ([-\d.]+)\)/)
          .map(Number);
        return { id: g.dataset.node, x, y, w: r.width, h: r.height };
      });
      const hits = [];
      for (const g of document.querySelectorAll("g[data-from]")) {
        const path = g.querySelector(".wb-edge-line");
        const length = path.getTotalLength();
        for (let d = 0; d <= length; d += 4) {
          const p = path.getPointAtLength(d);
          const box = boxes.find(
            (b) =>
              b.id !== g.dataset.from &&
              b.id !== g.dataset.to &&
              p.x > b.x + 1 &&
              p.x < b.x + b.w - 1 &&
              p.y > b.y + 1 &&
              p.y < b.y + b.h - 1,
          );
          if (box) {
            hits.push(`${g.dataset.from}->${g.dataset.to} through ${box.id}`);
            break;
          }
        }
      }
      return hits;
    });
    assert.deepEqual(crossings, []);
    await page
      .getByRole("button", { name: "Investigation path", exact: true })
      .click();
    await page.locator(".wb-relationship-groups summary").first().click();
    await page.locator(".wb-relationship-row").first().click();
    await page.locator(".wb-graph-inspector .wb-evidence-ref").click();
    await page.locator(".wb-raw-evidence").waitFor();
    await page.getByRole("button", { name: "Close evidence" }).click();
    await page.locator(".wb-relationship-groups summary").first().click();
    await page
      .getByRole("button", { name: "Reset graph", exact: true })
      .click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: join(artifacts, "investigation-path.png"),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Select Grey Moth", exact: true })
      .click();
    await page.locator(".wb-connection-list button").first().click();
    await page.locator(".wb-graph-inspector .wb-evidence-ref").click();
    await page.locator(".wb-raw-evidence").waitFor();
    await page.getByRole("button", { name: "Close evidence" }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: join(artifacts, "relationship-graph.png"),
      fullPage: true,
    });
  });
  await check("Evidence analysis and NIST categories", async () => {
    await page
      .getByRole("button", { name: "Continue to analysis", exact: true })
      .click();
    assert.equal(await page.evaluate(() => window.scrollY), 0);
    await page.getByRole("button", { name: "Run evidence analysis" }).click();
    await page
      .getByText(
        "Evidence rules evaluated. Findings reference only the attached observations.",
        { exact: true },
      )
      .waitFor();
    assert.match(
      await page.locator(".wb-analysis-summary").innerText(),
      /not an LLM/,
    );
    await page
      .getByRole("button", { name: "Review NIST alignment", exact: true })
      .click();
    assert.equal(await page.locator(".wb-nist-grid article").count(), 6);
    // Each function states its basis; detection and response cite case records.
    assert.equal(await page.locator(".wb-nist-basis").count(), 6);
    const respond = page
      .locator(".wb-nist-grid article")
      .filter({ hasText: "RESPOND" });
    assert.ok((await respond.locator(".wb-evidence-ref").count()) > 0);
    assert.match(
      await respond.locator(".wb-nist-actions").innerText(),
      /Isolate affected endpoint/,
    );
  });
  await check("Notebook persistence and HTML inertness", async () => {
    await page
      .getByLabel("Entry type", { exact: true })
      .selectOption("hypothesis");
    await page
      .getByLabel("Investigation note", { exact: true })
      .fill("Validate process ancestry. <img src=x onerror=alert(1)>");
    await page.getByRole("button", { name: "Save entry", exact: true }).click();
    await page.locator(".wb-notes article").waitFor();
    await page.reload({ waitUntil: "networkidle" });
    assert.match(
      await page.locator(".wb-notes").innerText(),
      /Validate process ancestry/,
    );
    assert.equal(await page.locator(".wb-notes img").count(), 0);
  });
  await check("Review, approve, simulate and advance case", async () => {
    await page
      .getByRole("button", {
        name: "Review response recommendations",
        exact: true,
      })
      .click();
    // Containment is gated on a reviewed simulation; the gate explains why.
    const advance = page.getByRole("button", {
      name: "Advance to containment",
      exact: true,
    });
    assert.ok(await advance.isDisabled());
    assert.match(
      await page.locator(".wb-stage-gate").innerText(),
      /containment or scoped hunt action/,
    );
    const card = page.locator(".wb-response-card").filter({
      has: page.getByRole("heading", {
        name: "Isolate affected endpoint",
        exact: true,
      }),
    });
    assert.equal(
      await card.getByRole("button", { name: "Run simulation" }).count(),
      0,
    );
    await card
      .getByRole("button", { name: "Approve recommendation", exact: true })
      .click();
    await card
      .getByRole("button", { name: "Run simulation", exact: true })
      .click();
    await card
      .getByText("Simulation recorded. No external system was changed.", {
        exact: true,
      })
      .waitFor();
    const trail = await page.locator(".wb-audit-list").innerText();
    assert.match(trail, /Analyst approval/);
    assert.match(trail, /Simulated action recorded/);
    assert.equal(await page.locator(".wb-stage-gate").count(), 0);
    await advance.click();
    await page
      .locator(".wb-case-stages .current")
      .filter({ hasText: "containment" })
      .waitFor();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: join(artifacts, "response-review.png"),
      fullPage: true,
    });
  });
  await check(
    "Report download contains evidence and analyst decisions",
    async () => {
      await page
        .getByRole("button", {
          name: "Review investigation report",
          exact: true,
        })
        .click();
      await page.locator(".wb-report-preview").waitFor();
      const reportSections = [
        "Executive summary",
        "Observed evidence",
        "Correlated context",
        "Automated interpretation",
        "Risk assessment",
        "NIST alignment",
        "Response recommendations",
        "Analyst decisions",
        "Audit trail",
      ];
      const headings = await page
        .locator(".wb-report-section > h3")
        .allTextContents();
      assert.equal(headings.length, reportSections.length);
      reportSections.forEach((title, i) =>
        assert.ok(headings[i].includes(title)),
      );
      assert.equal(
        await page
          .locator(".wb-report-preview img, .wb-report-preview script")
          .count(),
        0,
      );
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: join(artifacts, "investigation-report.png"),
        fullPage: false,
      });
      const [download] = await Promise.all([
        page.waitForEvent("download"),
        page
          .getByRole("button", { name: "Export report", exact: true })
          .click(),
      ]);
      const path = join(artifacts, "GOTHAMITE-INC-1042-example.md");
      await download.saveAs(path);
      const report = await readFile(path, "utf-8");
      let previousSection = -1;
      for (const title of reportSections) {
        const position = report.indexOf("## " + title);
        assert.ok(position > previousSection, title + " ordered in export");
        previousSection = position;
      }
      for (const text of [
        "SYNTHETIC EXERCISE",
        "Observed evidence",
        "Automated interpretation",
        "Analyst conclusions",
        "simulated",
        "Validate process ancestry",
      ])
        assert.ok(report.includes(text), text);
    },
  );
  await check(
    "Navigation, empty search, pagination and legacy persona graph",
    async () => {
      for (const [link, title] of [
        ["Threat actors", "Threat actors"],
        ["Assets", "Asset inventory"],
        ["Dark-web intelligence", "Dark-web intelligence"],
        ["Reports", "Investigation reports"],
      ]) {
        await page
          .getByRole("navigation", { name: "Main navigation" })
          .getByRole("link", { name: link, exact: true })
          .click();
        await page.getByRole("heading", { name: title, exact: true }).waitFor();
        if (link === "Dark-web intelligence") {
          assert.match(
            await page.locator(".wb-callout").innerText(),
            /corroboration/,
          );
          assert.equal(await page.locator(".wb-table tbody tr").count(), 4);
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.screenshot({
            path: join(artifacts, "dark-web-intelligence.png"),
            fullPage: true,
          });
        }
        await page.reload({ waitUntil: "networkidle" });
        await page.getByRole("heading", { name: title, exact: true }).waitFor();
      }
      await page.goto(url + "/intelligence?kind=indicator", {
        waitUntil: "networkidle",
      });
      await page.getByRole("button", { name: "Next", exact: true }).click();
      await page.getByText("Page 2 of 11", { exact: true }).waitFor();
      await page
        .getByRole("textbox", { name: "Search intelligence", exact: true })
        .fill("missing-indicator.example");
      await page.getByRole("button", { name: "Search", exact: true }).click();
      await page
        .getByRole("heading", { name: "No matching intelligence" })
        .waitFor();
      await page.goto(url + "/graph", { waitUntil: "networkidle" });
      assert.match(await page.locator("main").innerText(), /nightjar/i);
      await page
        .getByRole("navigation", { name: "Persona toolkit navigation" })
        .waitFor();
      assert.match(
        await page.locator(".wb-toolkit .wb-heading").innerText(),
        /Existing toolkit/i,
      );
      await page
        .getByRole("navigation", { name: "Persona toolkit navigation" })
        .getByRole("link", { name: "Overview", exact: true })
        .click();
      await page
        .locator(".wb-toolkit-content button:enabled")
        .filter({ hasText: "Run correlation pass" })
        .waitFor();
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: join(artifacts, "persona-toolkit.png"),
        fullPage: true,
      });
    },
  );
  await check("Tablet layout and keyboard global search", async () => {
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto(url + "/command", { waitUntil: "networkidle" });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    );
    await page.keyboard.press("Control+k");
    assert.equal(
      await page
        .getByRole("textbox", { name: "Global search", exact: true })
        .evaluate((el) => el === document.activeElement),
      true,
    );
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: join(artifacts, "tablet.png"),
      fullPage: true,
    });
  });
  assert.deepEqual(errors, [], "Browser console/page errors");
  console.log(
    JSON.stringify(
      { checks: results.length, browserErrors: errors.length, artifacts },
      null,
      2,
    ),
  );
} finally {
  if (browser) await browser.close();
  server.kill();
  await new Promise((r) =>
    server.exitCode !== null ? r() : server.once("exit", r),
  );
  // This directory was freshly created by mkdtemp for this isolated test only.
  await rm(temporary, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 150,
  });
}
