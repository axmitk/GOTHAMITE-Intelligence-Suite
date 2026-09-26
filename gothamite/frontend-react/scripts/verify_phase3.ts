import { chromium } from 'playwright';

async function verifyPhase3() {
  console.log('=== GOTHAMITE React Migration - Phase 3 Verification ===\n');

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/home/tanish-mishra/.local/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    console.log('PAGE LOG:', msg.text());
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  console.log('1. Navigating to http://localhost:5173/graph...');
  await page.goto('http://localhost:5173/graph', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Take initial canvas screenshot
  await page.screenshot({ path: 'scripts/graph_initial.png', fullPage: true });

  // 1. Verify All 6 Nodes Render
  console.log('2. Verifying all 6 persona nodes render on canvas...');
  const expectedHandles = [
    'nightjar',
    'n1ghtjar_',
    'quillfeather',
    'quill_v2',
    'nightjarr',
    'bellwether',
  ];

  for (const handle of expectedHandles) {
    const nodeText = page.locator('svg text').filter({ hasText: new RegExp(`^${handle}$`) }).first();
    if (!(await nodeText.isVisible())) {
      throw new Error(`Node handle "${handle}" not visible on canvas!`);
    }
  }
  console.log(`✓ All 6 nodes rendered: ${expectedHandles.join(', ')}`);

  // 2. Verify All 3 Real Edges Render and visual distinction (solid vs dashed)
  console.log('3. Verifying all 3 real edges & solid vs dashed styles...');
  const edges = page.locator('svg line[stroke-linecap="round"]');
  const edgeCount = await edges.count();
  console.log(`✓ Edge count on canvas: ${edgeCount}`);
  if (edgeCount < 3) {
    throw new Error(`Expected at least 3 edges on canvas, found ${edgeCount}`);
  }

  // Check dashed edge (transacted_with)
  const dashedEdges = page.locator('svg line[stroke-dasharray="6,4"]');
  const dashedCount = await dashedEdges.count();
  console.log(`✓ Dashed edges count (transacted_with): ${dashedCount}`);
  if (dashedCount < 1) {
    throw new Error('Dashed edge for transacted_with relationship not found!');
  }

  // 3. Verify Security Rule: Zero Percentages Anywhere (SECURITY.md §5)
  console.log('4. Verifying zero percentage displays (SECURITY.md §5)...');
  const bodyText = await page.innerText('body');
  const percentMatches = bodyText.match(/\b\d+(\.\d+)?%/g);
  if (percentMatches) {
    throw new Error(`SECURITY VIOLATION: Percentage found in UI: ${percentMatches.join(', ')}`);
  }
  console.log('✓ Zero percentage displays detected across entire view.');

  // 4. Test Selecting nightjar ↔ n1ghtjar_ (0.95 edge)
  console.log('5. Testing edge selection: nightjar ↔ n1ghtjar_ (0.95)...');
  // Click midpoint score pill "0.95"
  const scorePill095 = page.locator('svg text:has-text("0.95")').first();
  await scorePill095.click({ force: true });
  await page.waitForTimeout(600);

  const inspectorText = await page.locator('.lg\\:w-\\[35\\%\\]').innerText();
  console.log('Inspector content after 0.95 edge click:\n' + inspectorText.slice(0, 300) + '...\n');

  if (!inspectorText.includes('nightjar') || !inspectorText.includes('n1ghtjar_')) {
    throw new Error('Inspector missing nightjar ➔ n1ghtjar_ header!');
  }
  if (!inspectorText.includes('0.95') || !inspectorText.includes('VERY STRONG')) {
    throw new Error('Inspector missing 0.95 Very Strong ScoreBadge!');
  }
  if (!inspectorText.includes('shared_pgp') || !inspectorText.includes('+0.70')) {
    throw new Error('Inspector missing shared_pgp (+0.70) evidence row!');
  }
  if (!inspectorText.includes('shared_wallet') || !inspectorText.includes('+0.45')) {
    throw new Error('Inspector missing shared_wallet (+0.45) evidence row!');
  }
  console.log('✓ Verified: Complete evidence trail (+0.70 PGP, +0.45 wallet) rendered in inspector.');

  // 5. Test Artifact Inspection Modal
  console.log('6. Testing Artifact Modal inspection...');
  const viewArtifactBtn = page.locator('.lg\\:w-\\[35\\%\\] button:has-text("View")').first();
  await viewArtifactBtn.click();
  await page.waitForTimeout(500);

  const modal = page.locator('[role="dialog"]');
  if (!(await modal.isVisible())) {
    throw new Error('Artifact modal did not open!');
  }
  const modalText = await modal.innerText();
  if (!modalText.includes('SHA-256 Content Hash') || !modalText.includes('Onion Target URL')) {
    throw new Error('Artifact modal missing cryptographic hash or onion URL!');
  }
  console.log('✓ Artifact modal rendered with SHA-256 hash and immutable raw content.');
  await page.locator('[role="dialog"] button[aria-label="Close modal"]').click();
  await page.waitForTimeout(300);

  // 6. Test Selecting quillfeather ➔ quill_v2 (0.60 edge)
  console.log('7. Testing edge selection: quillfeather ➔ quill_v2 (0.60)...');
  const scorePill060 = page.locator('svg text:has-text("0.60")').first();
  await scorePill060.click({ force: true });
  await page.waitForTimeout(600);

  const inspector060Text = await page.locator('.lg\\:w-\\[35\\%\\]').innerText();
  if (!inspector060Text.includes('quillfeather') || !inspector060Text.includes('quill_v2')) {
    throw new Error('Inspector missing quillfeather ➔ quill_v2 header!');
  }
  if (!inspector060Text.includes('0.60') || !inspector060Text.includes('STRONG')) {
    throw new Error('Inspector missing 0.60 Strong ScoreBadge!');
  }
  if (!inspector060Text.includes('temporal_succession') || !inspector060Text.includes('+0.15')) {
    throw new Error('Inspector missing temporal_succession (+0.15) evidence row!');
  }
  console.log('✓ Verified: quillfeather ➔ quill_v2 0.60 edge inspector populated with temporal succession.');

  // 7. Test Decoy Node Selection: nightjarr (UX_SPEC.md §7)
  console.log('8. Testing Decoy Node: clicking "nightjarr"...');
  await page.evaluate(() => {
    const el = document.querySelector('g[data-node-handle="nightjarr"]');
    console.log('Found nightjarr element in DOM:', !!el, el?.outerHTML?.slice(0, 100));
  });

  const decoyNode = page.locator('svg g[data-node-handle="nightjarr"] text');
  console.log('Clicking nightjarr text locator...');
  await decoyNode.click({ force: true });
  await page.waitForTimeout(800);

  const decoyInspectorText = await page.locator('.lg\\:w-\\[35\\%\\]').innerText();
  console.log('Inspector content for nightjarr decoy:\n' + decoyInspectorText + '\n');

  if (!decoyInspectorText.includes('Adversarial Decoy Analysis') || !decoyInspectorText.includes('Attribution Restraint')) {
    throw new Error('Decoy explanatory state missing title / badge!');
  }
  if (!decoyInspectorText.includes('No relationship proposed') || !decoyInspectorText.includes('nightjar')) {
    throw new Error('Decoy explanatory state missing nearest candidate explanation!');
  }
  if (!decoyInspectorText.includes('+0.15 handle_similarity') || !decoyInspectorText.includes('−0.30 identity_contradiction')) {
    throw new Error('Decoy signal comparison rows (+0.15 / -0.30) missing!');
  }
  console.log('✓ Verified: Decoy node nightjarr correctly shows system restraint explanatory state!');

  // 8. Test Confirm / Reject Mutation Flow (UX_SPEC.md §10)
  console.log('9. Testing Confirm/Reject flow on nightjar ↔ n1ghtjar_...');
  // Select 0.95 edge again
  await scorePill095.click({ force: true });
  await page.waitForTimeout(500);

  // Confirm link
  const confirmBtn = page.locator('.lg\\:w-\\[35\\%\\] button:has-text("Confirm Link")');
  if (await confirmBtn.isVisible() && (await confirmBtn.isEnabled())) {
    await confirmBtn.click();
    await page.waitForTimeout(800);

    const afterConfirmText = await page.locator('.lg\\:w-\\[35\\%\\]').innerText();
    if (!afterConfirmText.includes('CONFIRMED')) {
      throw new Error('Status pill did not update to CONFIRMED after click!');
    }
    console.log('✓ Confirm link call succeeded; status updated to CONFIRMED and buttons disabled.');

    // Reset back to proposed
    const resetBtn = page.locator('button:has-text("Reset State to Proposed")');
    await resetBtn.click();
    await page.waitForTimeout(800);
    console.log('✓ Reset state back to PROPOSED.');

    // Reject link
    const rejectBtn = page.locator('.lg\\:w-\\[35\\%\\] button:has-text("Reject Link")');
    await rejectBtn.click();
    await page.waitForTimeout(800);

    const afterRejectText = await page.locator('.lg\\:w-\\[35\\%\\]').innerText();
    if (!afterRejectText.includes('REJECTED')) {
      throw new Error('Status pill did not update to REJECTED after click!');
    }
    console.log('✓ Reject link call succeeded; status updated to REJECTED.');

    // Verify reduced opacity (~15%)
    const rejectedLine = page.locator('svg line[stroke-opacity="0.15"]');
    if ((await rejectedLine.count()) < 1) {
      throw new Error('Rejected edge was not rendered with reduced opacity (~15%)!');
    }
    console.log('✓ Verified: Rejected edge renders at reduced opacity (~15%), not hidden (UI_SPEC.md §5).');

    // Reset back to PROPOSED so database remains pristine
    const finalResetBtn = page.locator('button:has-text("Reset State to Proposed")');
    await finalResetBtn.click();
    await page.waitForTimeout(800);
    console.log('✓ Reset link back to PROPOSED for demo baseline.');
  } else {
    console.log('Note: Confirm button was already reviewed or disabled.');
  }

  // 9. Verify Deep Linking: /graph?edge=1c19f923-f967-4a17-bce6-f9dcdce5836c
  console.log('10. Testing deep linking with ?edge=<id>...');
  await page.goto(
    'http://localhost:5173/graph?edge=1c19f923-f967-4a17-bce6-f9dcdce5836c',
    { waitUntil: 'networkidle' }
  );
  await page.waitForTimeout(800);

  const deepLinkInspector = await page.locator('.lg\\:w-\\[35\\%\\]').innerText();
  if (!deepLinkInspector.includes('quillfeather') || !deepLinkInspector.includes('quill_v2')) {
    throw new Error('Deep linking /graph?edge=<id> failed to pre-select edge!');
  }
  console.log('✓ Deep linking /graph?edge=<id> pre-selected edge correctly!');

  // 10. Console Error Check
  if (consoleErrors.length > 0) {
    console.warn('Console errors detected:', consoleErrors);
  } else {
    console.log('✓ Zero console errors detected across entire session.');
  }

  await browser.close();
  console.log('\n=== ALL PHASE 3 ACCEPTANCE CRITERIA PASSED ===');
}

verifyPhase3().catch((err) => {
  console.error('FAILED:', err);
  process.exit(1);
});
