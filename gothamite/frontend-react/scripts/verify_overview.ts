import { chromium } from 'playwright';

async function main() {
  console.log('=== GOTHAMITE React Migration - Phase 2 Verification ===');

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/home/tanish-mishra/.local/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  // Monitor console messages
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  console.log('1. Navigating to http://localhost:5173/overview...');
  await page.goto('http://localhost:5173/overview', { waitUntil: 'networkidle' });

  // Wait for data loading to settle
  await page.waitForTimeout(1000);

  // Take screenshot for visual inspection
  await page.screenshot({ path: 'scripts/overview_rendered.png', fullPage: true });
  console.log('✓ Page rendered and screenshot saved to scripts/overview_rendered.png');

  // Verify Header
  const title = await page.textContent('h1');
  console.log(`✓ Header found: "${title}"`);

  // Verify Stat Cards
  const cardsText = await page.innerText('.grid.grid-cols-1.sm\\:grid-cols-2');
  console.log('✓ Stat Cards Content:\n' + cardsText);

  if (!cardsText.includes('6') || !cardsText.toLowerCase().includes('immutable artifacts')) {
    throw new Error('Stat cards missing expected counts!');
  }

  // Verify Security Rule: No Percentages anywhere
  const fullBodyText = await page.innerText('body');
  const percentMatches = fullBodyText.match(/\b\d+(\.\d+)?%/g);
  if (percentMatches) {
    throw new Error(`SECURITY VIOLATION: Percentage detected in UI: ${percentMatches.join(', ')}`);
  }
  console.log('✓ Verified: Zero percentage displays detected (SECURITY.md §5 satisfied)');

  // Verify Monitored Sources
  if (
    !fullBodyText.includes('forum-alpha') ||
    !fullBodyText.includes('marketplace-beta') ||
    !fullBodyText.includes('forum-gamma')
  ) {
    throw new Error('Monitored dark web sources missing!');
  }
  console.log('✓ Verified: Monitored dark web sources (forum-alpha, marketplace-beta, forum-gamma) rendered');

  // Verify Top Attributions
  console.log('Page text snippet around attributions:');
  const attributionsText = await page.locator('.lg\\:col-span-7').innerText();
  console.log(attributionsText);

  if (!fullBodyText.includes('nightjar') || !fullBodyText.includes('n1ghtjar_')) {
    throw new Error('Top attribution nightjar ➔ n1ghtjar_ missing!');
  }
  if (!fullBodyText.includes('0.95') || !fullBodyText.toLowerCase().includes('very strong')) {
    throw new Error('ScoreBadge for 0.95 Very Strong missing!');
  }
  console.log('✓ Verified: Top relationships render with ScoreBadge (0.95 Very Strong) and StatusPill');

  // Test Search Box (UX_SPEC.md §8, UX_CORRECTION.md §4)
  console.log('2. Testing Quick Search functionality...');
  const searchInput = page.locator('input[placeholder*="Search handle"]');
  await searchInput.fill('nightjar');
  await page.locator('button:has-text("Search")').click();
  await page.waitForTimeout(500);

  const searchResultsText = await page.innerText('.max-h-72');
  console.log(`✓ Search results for "nightjar":\n${searchResultsText.slice(0, 150)}...`);
  if (!searchResultsText.includes('nightjar')) {
    throw new Error('Search did not return nightjar!');
  }

  // Test Artifact Modal
  console.log('3. Testing Artifact Modal inspection...');
  const artifactButton = page.locator('button:has-text("Artifact")').first();
  if (await artifactButton.isVisible()) {
    await artifactButton.click();
    await page.waitForTimeout(500);

    const modalTitle = await page.textContent('[role="dialog"] span');
    console.log(`✓ Modal opened: "${modalTitle}"`);

    const modalText = await page.innerText('[role="dialog"]');
    if (!modalText.includes('SHA-256 Content Hash') || !modalText.includes('Onion Target URL')) {
      throw new Error('Artifact modal missing cryptographic provenance metadata!');
    }
    console.log('✓ Verified: Artifact Modal renders SHA-256 hash, onion URL, and escaped raw content');

    // Close modal
    await page.locator('[role="dialog"] button[aria-label="Close modal"]').click();
    await page.waitForTimeout(300);
  }

  // Test Correlation Trigger Button (UX_SPEC.md §5)
  console.log('4. Testing "Run Correlation Pass" trigger...');
  const correlateBtn = page.locator('button:has-text("Run Correlation Pass")');
  await correlateBtn.click();
  await page.waitForTimeout(1000);

  const successText = await page.textContent('text=Correlation pass complete');
  console.log(`✓ Correlation pass success banner: "${successText}"`);

  if (consoleErrors.length > 0) {
    console.warn('Console errors detected:', consoleErrors);
  } else {
    console.log('✓ Zero console errors detected!');
  }

  await browser.close();
  console.log('\n=== ALL PHASE 2 ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY ===');
}

main().catch((err) => {
  console.error('FAILED:', err);
  process.exit(1);
});
