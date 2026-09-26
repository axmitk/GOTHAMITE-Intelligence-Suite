import { chromium } from 'playwright';

async function verifyPhase4() {
  console.log('=== GOTHAMITE React Migration - Phase 4 Verification ===\n');

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/home/tanish-mishra/.local/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.error('PAGE ERROR:', msg.text());
    }
  });

  // ----------------------------------------------------
  // TEST 1: Dossier Default Route & Profile Verification
  // ----------------------------------------------------
  console.log('1. Navigating to http://localhost:5173/dossier...');
  await page.goto('http://localhost:5173/dossier', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Check URL redirected to a specific dossier (e.g. /dossier/cc7778c3...)
  const currentUrl = page.url();
  console.log(`Current Dossier URL: ${currentUrl}`);
  if (!currentUrl.includes('/dossier/')) {
    throw new Error(`Expected URL to redirect to a specific persona dossier, got ${currentUrl}`);
  }

  // Profile Header checks
  const headerHandle = await page.locator('h2.font-mono').first().innerText();
  console.log(`✓ Dossier Profile Header Handle: ${headerHandle}`);
  if (!headerHandle) {
    throw new Error('Dossier profile header handle is missing!');
  }

  // Activity Window & Post count
  const dossierMetrics = await page.locator('.grid-cols-2.sm\\:grid-cols-4').first().innerText();
  console.log(`✓ Dossier Metrics: \n${dossierMetrics}`);
  const dossierMetricsUpper = dossierMetrics.toUpperCase();
  if (!dossierMetricsUpper.includes('ACTIVITY WINDOW') || !dossierMetricsUpper.includes('TOTAL POSTS')) {
    throw new Error('Dossier activity metrics grid missing required fields!');
  }

  // Digital Identifiers & MonoValue
  console.log('2. Verifying Digital Identifiers (PGP & Wallets)...');
  const identifiersSection = page.locator('text=Digital Identifiers').first();
  if (!(await identifiersSection.isVisible())) {
    throw new Error('Digital Identifiers section not visible on Dossier!');
  }

  const monoBlocks = page.locator('button[title="Copy to clipboard"]');
  const copyBtnCount = await monoBlocks.count();
  console.log(`✓ Found ${copyBtnCount} copyable identifier blocks.`);
  if (copyBtnCount < 1) {
    throw new Error('Expected at least one copyable MonoValue identifier block!');
  }

  // Artifact Modal from Dossier Identifier
  console.log('3. Testing Artifact Inspection from Dossier...');
  const viewSourceBtn = page.locator('button:has-text("View Source")').first();
  if (await viewSourceBtn.isVisible()) {
    await viewSourceBtn.click();
    await page.waitForTimeout(400);

    const hashLocator = page.locator('text=SHA-256 Content Hash');
    await hashLocator.waitFor({ state: 'visible', timeout: 5000 });

    const modal = page.locator('[role="dialog"]');
    const modalText = await modal.innerText();
    if (!modalText.includes('SHA-256 Content Hash') || !modalText.includes('RAW SCRAPED CONTENT')) {
      throw new Error('Artifact modal missing SHA-256 verification or content!');
    }
    console.log('✓ Artifact modal rendered correctly from Dossier.');
    await page.locator('[role="dialog"] button[aria-label="Close modal"]').click();
    await page.waitForTimeout(400);
  }

  // Cross-Source Linkages & Jump to Graph
  console.log('4. Testing Cross-Source Linkages & "Jump to Graph Edge"...');
  const jumpToGraphBtn = page.locator('button:has-text("Jump to Graph Edge")').first();
  if (await jumpToGraphBtn.isVisible()) {
    await jumpToGraphBtn.click();
    await page.waitForTimeout(800);

    const graphUrl = page.url();
    console.log(`Navigated to Graph URL: ${graphUrl}`);
    if (!graphUrl.includes('/graph?edge=')) {
      throw new Error(`"Jump to Graph Edge" did not navigate to /graph?edge=<id>, got ${graphUrl}`);
    }

    // Verify Graph Inspector loaded
    const confidenceHeader = page.locator('text=Confidence Score');
    await confidenceHeader.waitFor({ state: 'visible', timeout: 5000 });
    const inspectorText = await page.locator('.lg\\:w-\\[35\\%\\]').innerText();
    if (!inspectorText.toUpperCase().includes('CONFIDENCE SCORE')) {
      throw new Error('Graph inspector failed to display after jumping from Dossier!');
    }
    console.log('✓ "Jump to Graph Edge" successfully navigated to Graph and selected edge.');
  }

  // Take Dossier Screenshot
  await page.goto(currentUrl, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'scripts/dossier_rendered.png', fullPage: true });
  console.log('✓ Dossier screenshot saved to scripts/dossier_rendered.png');

  // ----------------------------------------------------
  // TEST 2: Dossier Multi-Vector Search (UX_SPEC.md §8)
  // ----------------------------------------------------
  console.log('5. Testing Multi-Vector Entity Search on Dossier...');
  const searchInput = page.locator('input[placeholder*="Search handle"]');
  await searchInput.fill('quillfeather');
  await page.locator('form button:has-text("Search")').click();
  await page.waitForTimeout(600);

  const searchResultBtn = page.locator('button:has-text("Open Dossier")').first();
  if (!(await searchResultBtn.isVisible())) {
    throw new Error('Search for "quillfeather" did not return dropdown results!');
  }
  await searchResultBtn.click();
  await page.waitForTimeout(600);

  const quillHeader = await page.locator('h2.font-mono').first().innerText();
  if (!quillHeader.includes('quillfeather')) {
    throw new Error(`Expected dossier header to be quillfeather after search, got ${quillHeader}`);
  }
  console.log('✓ Multi-vector search found "quillfeather" and navigated to its dossier.');

  // Test wallet search
  await searchInput.fill('1Kp7dR3z');
  await page.locator('form button:has-text("Search")').click();
  await page.waitForTimeout(600);
  const walletResult = page.locator('button:has-text("Matched via")').first();
  if (!(await walletResult.isVisible())) {
    throw new Error('Search for wallet "1Kp7dR3z" did not return results!');
  }
  console.log('✓ Wallet address search successfully returned matching personas.');
  await page.locator('button:has-text("Clear")').click();
  await page.waitForTimeout(200);

  // ----------------------------------------------------
  // TEST 3: Decoy Node Dossier (nightjarr)
  // ----------------------------------------------------
  console.log('6. Testing Decoy Node Dossier (nightjarr)...');
  // Select nightjarr from dropdown
  const selectDropdown = page.locator('select').first();
  await selectDropdown.selectOption({ label: 'nightjarr (forum-gamma)' });
  await page.waitForTimeout(600);

  const decoyHeader = await page.locator('h2.font-mono').first().innerText();
  if (!decoyHeader.includes('nightjarr')) {
    throw new Error(`Expected nightjarr dossier header, got ${decoyHeader}`);
  }
  const decoyBody = await page.innerText('body');
  if (!decoyBody.includes('No cross-source relationships proposed or confirmed')) {
    throw new Error('Decoy nightjarr should show zero cross-source relationships!');
  }
  console.log('✓ Decoy node nightjarr correctly reflects zero cross-source attributions.');

  // ----------------------------------------------------
  // TEST 4: Timeline 6 Lanes & Quill Gap Visuals
  // ----------------------------------------------------
  console.log('7. Navigating to http://localhost:5173/timeline...');
  await page.goto('http://localhost:5173/timeline', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Spotlight Callout Banner
  const spotlight = page.locator('text=quillfeather ➔ quill_v2 (17-day succession gap)');
  if (!(await spotlight.isVisible())) {
    throw new Error('Timeline Spotlight callout banner for Quill handoff missing!');
  }
  console.log('✓ Quill handoff spotlight callout banner rendered.');

  // 6 Lanes Verification
  console.log('8. Verifying all 6 persona lanes render in juxtaposed order...');
  const expectedLanes = [
    'nightjar',
    'n1ghtjar_',
    'quillfeather',
    'quill_v2',
    'nightjarr',
    'bellwether',
  ];

  for (const handle of expectedLanes) {
    const laneBtn = page
      .locator('button[title="Open persona dossier"]')
      .filter({ hasText: new RegExp(`^${handle}$`) })
      .first();
    if (!(await laneBtn.isVisible())) {
      throw new Error(`Timeline lane for "${handle}" not visible!`);
    }
  }
  console.log(`✓ All 6 lanes rendered: ${expectedLanes.join(', ')}`);

  // Visual 17-Day Gap Marker (UI_SPEC.md §5, MIGRATION_PLAN.md Phase 4 item 3)
  console.log('9. Verifying visual 17-Day Gap marker...');
  const gapMarker = page.locator('text=17-Day Gap');
  if (!(await gapMarker.isVisible())) {
    throw new Error('17-Day Gap visual marker between quillfeather and quill_v2 is missing!');
  }
  console.log('✓ 17-Day Gap marker is clearly rendered between adjacent quill lanes.');

  // Synchronized Hover Interaction (UX_SPEC.md §9)
  console.log('10. Testing synchronized hover interaction on Quill migration...');
  const quillfeatherLane = page.locator('div.group:has-text("quillfeather")');
  await quillfeatherLane.hover();
  await page.waitForTimeout(300);

  // Check that quill_v2 bar receives highlight class (ring-2 ring-accent-cyan)
  const highlightedBars = page.locator('.ring-2.ring-accent-cyan');
  const highlightedCount = await highlightedBars.count();
  console.log(`Highlighted bars on hover: ${highlightedCount}`);
  if (highlightedCount < 2) {
    throw new Error(`Expected both quill bars to be highlighted synchronously on hover, found ${highlightedCount}`);
  }
  console.log('✓ Verified: quillfeather and quill_v2 bars highlight synchronously on hover!');

  // Click Bar Navigation to Dossier (UX_SPEC.md §9)
  console.log('11. Testing activity bar click navigation to Dossier...');
  const quillV2Bar = page.locator('div[title*="quill_v2"]').first();
  await quillV2Bar.click();
  await page.waitForTimeout(800);

  const barNavUrl = page.url();
  console.log(`Navigated to: ${barNavUrl}`);
  if (!barNavUrl.includes('/dossier/')) {
    throw new Error(`Clicking timeline bar did not navigate to /dossier/<id>, got ${barNavUrl}`);
  }
  const landedHandle = await page.locator('h2.font-mono').first().innerText();
  if (!landedHandle.includes('quill_v2')) {
    throw new Error(`Expected to land on quill_v2 dossier, got ${landedHandle}`);
  }
  console.log('✓ Timeline bar click successfully navigated to quill_v2 dossier.');

  // Return to Timeline
  await page.goto('http://localhost:5173/timeline', { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);

  // ----------------------------------------------------
  // TEST 5: Chronological Observation Stream & Filters
  // ----------------------------------------------------
  console.log('12. Testing Chronological Observation Stream & Filters...');
  const streamHeader = await page.locator('h3:has-text("Chronological Observation Stream")').innerText();
  console.log(`✓ Stream header: ${streamHeader}`);

  // Test Persona Filter
  const personaSelect = page.locator('select[aria-label="Filter by persona"]');
  await personaSelect.selectOption({ label: 'quill_v2' });
  await page.waitForTimeout(400);

  const filteredPersonaCountText = await page.locator('h3:has-text("Chronological Observation Stream")').innerText();
  console.log(`✓ Filtered by quill_v2: ${filteredPersonaCountText}`);

  // Reset persona filter before testing source filter
  await personaSelect.selectOption({ label: 'All Personas' });
  await page.waitForTimeout(400);

  // Test Source Filter
  const sourceSelect = page.locator('select[aria-label="Filter by source"]');
  await sourceSelect.selectOption({ label: 'forum-gamma' });
  await page.waitForTimeout(400);

  const filteredSourceCountText = await page.locator('h3:has-text("Chronological Observation Stream")').innerText();
  console.log(`✓ Filtered by forum-gamma: ${filteredSourceCountText}`);

  // Reset filters
  await sourceSelect.selectOption({ label: 'All Sources' });
  await page.waitForTimeout(400);

  // Test Artifact Modal from Stream
  const streamArtifactBtn = page.locator('button:has-text("View Artifact")').first();
  if (await streamArtifactBtn.isVisible()) {
    await streamArtifactBtn.click();
    const hashLocator = page.locator('text=SHA-256 Content Hash');
    await hashLocator.waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('[role="dialog"] button[aria-label="Close modal"]').click();
    await page.waitForTimeout(400);
    console.log('✓ Stream artifact inspection modal verified.');
  }

  // Take Timeline Screenshot
  await page.screenshot({ path: 'scripts/timeline_rendered.png', fullPage: true });
  console.log('✓ Timeline screenshot saved to scripts/timeline_rendered.png');

  // ----------------------------------------------------
  // TEST 6: Search on Overview & Graph (Acceptance Item 5)
  // ----------------------------------------------------
  console.log('13. Testing Search navigation from Overview & Graph...');
  // Overview search
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const ovSearchInput = page.locator('input[placeholder*="Search handle"]');
  await ovSearchInput.fill('nightjar');
  await page.locator('form button:has-text("Search")').click();
  await page.waitForTimeout(500);
  const ovResult = page.locator('button:has-text("View Dossier")').first();
  if (!(await ovResult.isVisible())) {
    throw new Error('Overview search did not show results for "nightjar"!');
  }
  await ovResult.click();
  await page.waitForTimeout(600);
  if (!page.url().includes('/dossier/')) {
    throw new Error(`Overview search result click did not navigate to /dossier/<id>, got ${page.url()}`);
  }
  console.log('✓ Overview search navigated to Dossier successfully.');

  // Graph search
  await page.goto('http://localhost:5173/graph', { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const graphSearchInput = page.locator('input[placeholder*="Search handle"]');
  await graphSearchInput.fill('quill');
  await page.locator('form button:has-text("Find")').click();
  await page.waitForTimeout(500);
  const graphResult = page.locator('button:has-text("Focus")').first();
  if (!(await graphResult.isVisible())) {
    throw new Error('Graph search did not show results for "quill"!');
  }
  await graphResult.click();
  await page.waitForTimeout(600);
  console.log('✓ Graph search successfully found and focused node.');

  // ----------------------------------------------------
  // TEST 7: Security Audit - Zero Percentages (SECURITY.md §5)
  // ----------------------------------------------------
  console.log('14. Security Check: Verifying zero percentage displays across Dossier and Timeline...');
  // Check Dossier
  await page.goto('http://localhost:5173/dossier', { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const dossierText = await page.innerText('body');
  const dossierPercentages = dossierText.match(/\b\d+(\.\d+)?%/g);
  if (dossierPercentages) {
    throw new Error(`SECURITY VIOLATION on Dossier: Found percentage in UI: ${dossierPercentages.join(', ')}`);
  }

  // Check Timeline
  await page.goto('http://localhost:5173/timeline', { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const timelineText = await page.innerText('body');
  const timelinePercentages = timelineText.match(/\b\d+(\.\d+)?%/g);
  if (timelinePercentages) {
    throw new Error(`SECURITY VIOLATION on Timeline: Found percentage in UI: ${timelinePercentages.join(', ')}`);
  }
  console.log('✓ Zero percentages detected on both Dossier and Timeline pages.');

  // ----------------------------------------------------
  // TEST 8: Console Errors Check
  // ----------------------------------------------------
  console.log('15. Checking browser console errors...');
  if (consoleErrors.length > 0) {
    console.error('Console errors logged:', consoleErrors);
    throw new Error(`Encountered ${consoleErrors.length} console errors during Phase 4 verification.`);
  }
  console.log('✓ Zero console errors detected across all test sequences.');

  await browser.close();
  console.log('\n=== ALL PHASE 4 ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY ===');
}

verifyPhase4().catch((err) => {
  console.error('VERIFICATION FAILED:', err);
  process.exit(1);
});
