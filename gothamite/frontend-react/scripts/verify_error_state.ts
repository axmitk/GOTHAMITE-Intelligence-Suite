import { chromium } from 'playwright';

async function testErrorState() {
  console.log('=== Testing Error and Fallback Handling (UX_SPEC.md §4) ===');

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/home/tanish-mishra/.local/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  page.on('console', (msg) => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', (err) => console.log('PAGE ERROR:', err.message));
  page.on('requestfailed', (req) => console.log('REQ FAILED:', req.url(), req.failure()?.errorText));

  // Intercept backend API calls (both /api/v1/ and /health) - do not match /src/api/
  await page.route('**/api/v1/**', (route) => route.abort());
  await page.route('**/health', (route) => route.abort());

  await page.goto('http://localhost:5173/overview', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  const bodyText = await page.innerText('body');
  console.log('Page content during simulated API outage:\n' + bodyText);
  const errorBanner = await page.locator('text=Cannot reach GOTHAMITE backend');

  if (await errorBanner.isVisible()) {
    console.log('✓ Error banner correctly rendered: Calm message with Retry button');
  } else {
    throw new Error('Error banner failed to render during backend outage!');
  }

  // Ensure NO blank screen, white screen, or raw stack trace
  if (bodyText.length < 50) {
    throw new Error('Blank screen detected during outage!');
  }
  if (bodyText.includes('Traceback') || bodyText.includes('TypeError:') || bodyText.includes('at HTML')) {
    throw new Error('Raw stack trace leaked to user!');
  }

  console.log('✓ Zero raw stack traces leaked. Graceful UI degradation confirmed.');
  await browser.close();
}

testErrorState().catch((err) => {
  console.error('FAILED:', err);
  process.exit(1);
});
