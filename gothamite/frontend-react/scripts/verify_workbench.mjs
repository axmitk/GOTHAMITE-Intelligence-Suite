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
    // Four exercise cases, the dataset-backed INC-1046 review case and the
    // six-case library (INC-1047 to INC-1052).
    const queue = await page.locator(".wb-table tbody").innerText();
    assert.equal(await page.locator(".wb-table tbody tr").count(), 11);
    for (const id of [
      "INC-1042",
      "INC-1043",
      "INC-1044",
      "INC-1045",
      "INC-1046",
      "INC-1047",
      "INC-1048",
      "INC-1049",
      "INC-1050",
      "INC-1051",
      "INC-1052",
    ])
      assert.match(queue, new RegExp(id));
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
    // Adapter enrichment is present but synthetic: no live collection by default.
    await page.locator(".wb-source-obs article").first().waitFor();
    const sourceObs = await page.locator(".wb-source-obs").innerText();
    assert.match(sourceObs, /HORUS/);
    assert.match(sourceObs, /collection status: synthetic/i);
    assert.doesNotMatch(sourceObs, /status: connected/i);
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
    await page.locator(".wb-nist-basis").first().waitFor();
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
          // Four exercise bulletins plus the INC-1051 library bulletin.
          assert.equal(await page.locator(".wb-table tbody tr").count(), 5);
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
      await page.getByText(/^Page 2 of \d+$/).waitFor();
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
  await check(
    "Dataset-derived evidence, provenance, graph and report",
    async () => {
      await page.setViewportSize({ width: 1440, height: 1060 });
      // 1-4. Search a dataset-derived indicator and inspect its provenance.
      await page.goto(url + "/intelligence?q=claudfront.net", {
        waitUntil: "networkidle",
      });
      const row = page.locator(".wb-table tbody tr").first();
      assert.match(await row.innerText(), /claudfront\.net/);
      assert.match(
        await row.locator(".wb-prov").innerText(),
        /dataset-derived/i,
      );
      await row.locator("a").first().click();
      await page.getByRole("heading", { name: "claudfront.net" }).waitFor();
      assert.match(
        await page.locator(".wb-dataset-record").first().innerText(),
        /CC BY 4\.0/,
      );
      // Each report listing stays a separate supporting observation.
      assert.ok((await page.locator(".wb-evidence-row").count()) >= 2);
      await page.locator(".wb-evidence-row").first().click();
      await page.locator(".wb-drawer .wb-dataset-record").waitFor();
      assert.match(
        await page.locator(".wb-drawer").innerText(),
        /Infoblox Threat Intelligence indicators/,
      );
      await page.getByRole("button", { name: "Close evidence" }).click();
      // 7-8. Graph shows the indicator linked to its source reports.
      await page
        .getByRole("button", { name: "Relationship graph", exact: true })
        .click();
      await page.locator(".wb-graph-node").first().waitFor();
      assert.ok(
        (await page.locator("g[data-node^='DS-REPORT-']").count()) >= 2,
      );
      // 5-6. Forum and marketplace views over the same observation model.
      await page.goto(url + "/dark-web?kind=forum_thread", {
        waitUntil: "networkidle",
      });
      assert.ok((await page.locator(".wb-table tbody tr").count()) > 0);
      assert.match(
        await page.locator(".wb-table tbody").innerText(),
        /dataset-derived/i,
      );
      await page
        .getByRole("button", { name: "Marketplace listings", exact: true })
        .click();
      await page.waitForLoadState("networkidle");
      await page
        .locator(".wb-table tbody .wb-prov.reference_derived")
        .first()
        .waitFor();
      assert.match(
        await page.locator(".wb-table tbody").innerText(),
        /reference reconstruction/i,
      );
      assert.doesNotMatch(
        await page.locator(".wb-table tbody").innerText(),
        /dataset-derived/i,
      );
      // 9-11. Dataset-backed case and report keep provenance.
      await page.goto(url + "/investigations/INC-1046?view=report", {
        waitUntil: "networkidle",
      });
      await page.locator(".wb-report-preview").waitFor();
      const report = await page.locator(".wb-report-preview").innerText();
      assert.match(report, /Dataset-derived evidence:/);
      assert.match(report, /Evidence sources/i);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: join(artifacts, "dataset-case-report.png"),
        fullPage: false,
      });
      // 12. The canonical IOC is still the synthetic exercise record.
      await page.goto(url + "/intelligence?q=203.0.113.42", {
        waitUntil: "networkidle",
      });
      assert.match(
        await page.locator(".wb-table tbody tr").first().innerText(),
        /203\.0\.113\.42[\s\S]*synthetic/i,
      );
    },
  );
  await check(
    "TOR-associated IOC, enrichment, graph, case and report",
    async () => {
      // 1. The IOC from synthetic telemetry stays synthetic in search.
      await page.goto(url + "/intelligence?q=185.220.100.242", {
        waitUntil: "networkidle",
      });
      const row = page.locator(".wb-table tbody tr").first();
      assert.match(
        await row.innerText(),
        /185\.220\.100\.242[\s\S]*synthetic/i,
      );
      await row.locator("a").first().click();
      await page.getByRole("heading", { name: "185.220.100.242" }).waitFor();
      // 2. Enrichment: small text badge and a TOR infrastructure panel.
      await page.locator(".wb-tor-context").first().waitFor();
      assert.equal(await page.locator(".wb-heading .wb-tor").count(), 1);
      const tor = await page.locator(".wb-tor-context").first().innerText();
      assert.match(tor, /Exit node\s*Yes/i);
      assert.match(tor, /Tor Project Onionoo/);
      assert.match(tor, /2026-09-28 17:00:00 UTC/);
      assert.doesNotMatch(
        await page.locator("main").innerText(),
        /live tor monitoring/i,
      );
      await page.screenshot({
        path: join(artifacts, "tor-ioc-profile.png"),
        fullPage: false,
      });
      // 3. Evidence: the Onionoo observation keeps its provenance.
      const torRow = page
        .locator(".wb-evidence-row")
        .filter({ hasText: "TOR exit node:" })
        .first();
      assert.match(await torRow.innerText(), /dataset-derived/i);
      await torRow.click();
      await page.locator(".wb-drawer .wb-tor-context").waitFor();
      const drawer = await page.locator(".wb-drawer").innerText();
      assert.match(drawer, /Tor Project Onionoo relay metadata/);
      assert.match(drawer, /CC0/);
      await page.getByRole("button", { name: "Close evidence" }).click();
      // 4. Case: Tor context is a low, separate risk dimension.
      await page.goto(url + "/investigations/INC-1047?view=analysis", {
        waitUntil: "networkidle",
      });
      const risk = await page.locator(".wb-risk-factors").innerText();
      assert.match(risk, /TOR exit-node context[\s\S]*TOR context[\s\S]*\+5/i);
      assert.doesNotMatch(risk, /Malicious reputation/);
      // 5. Graph: IP --ASSOCIATED_WITH--> Tor relay, evidence-backed.
      await page.goto(url + "/investigations/INC-1047?view=graph", {
        waitUntil: "networkidle",
      });
      await page.locator(".wb-graph-node").first().waitFor();
      const full = page.getByRole("button", {
        name: "Full graph",
        exact: true,
      });
      if (await full.count()) await full.click();
      assert.ok(
        (await page.locator("g[data-node^='DS-TOR_RELAY-']").count()) >= 1,
      );
      await page.screenshot({
        path: join(artifacts, "tor-case-graph.png"),
        fullPage: false,
      });
      // 6. Report: synthetic telemetry and dataset-derived Tor context stay distinct.
      await page.goto(url + "/investigations/INC-1047?view=report", {
        waitUntil: "networkidle",
      });
      await page.locator(".wb-report-preview").waitFor();
      const report = await page.locator(".wb-report-preview").innerText();
      assert.match(report, /Tor Project Onionoo relay metadata/);
      assert.match(report, /Synthetic demonstration evidence/);
      // 7. The library cases open and keep their own states.
      for (const [id, state] of [
        ["INC-1048", "CONTAINMENT"],
        ["INC-1052", "CLOSED"],
      ]) {
        await page.goto(url + `/investigations/${id}`, {
          waitUntil: "networkidle",
        });
        assert.match(
          await page.locator("main").innerText(),
          new RegExp(state, "i"),
        );
      }
    },
  );
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
