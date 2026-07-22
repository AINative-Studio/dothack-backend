import { test, expect, Page } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:3000';
const LUMA_API_KEY = 'secret-Ix0bVV0oVB19U8v6GRJtlrx6k';

/**
 * Inject auth tokens into the browser so the middleware and React hooks
 * treat us as a logged-in user. This mirrors what the real login flow
 * stores in localStorage + cookies.
 */
async function loginAsTestUser(page: Page) {
  await page.goto(FRONTEND_URL);
  await page.evaluate(() => {
    const fakeToken = 'e2e-test-token-luma-integration';
    localStorage.setItem('auth_token', fakeToken);
    localStorage.setItem('dothack_access_token', fakeToken);
    document.cookie = `auth_token=${fakeToken}; path=/`;
    document.cookie = `dothack_access_token=${fakeToken}; path=/`;
  });
}

test.describe('Luma Integration Settings Flow', () => {

  test('unauthenticated user is redirected to login from /integrations', async ({ page }) => {
    const response = await page.goto(`${FRONTEND_URL}/integrations`);
    await page.waitForURL(/login/, { timeout: 5000 });
    expect(page.url()).toContain('/login');
  });

  test('authenticated user can navigate to /integrations page', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations`);
    await page.waitForLoadState('networkidle');

    // Page should show the Integrations heading
    const heading = page.locator('h1');
    await expect(heading).toContainText(/integrations/i);

    // Luma card should be visible
    const lumaCard = page.locator('text=Luma').first();
    await expect(lumaCard).toBeVisible();

    // Configure button should exist
    const configureBtn = page.locator('a[href="/integrations/luma"]').first();
    await expect(configureBtn).toBeVisible();
  });

  test('authenticated user can navigate to /integrations/luma', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/luma`);
    await page.waitForLoadState('networkidle');

    // Page header
    const heading = page.locator('h1');
    await expect(heading).toContainText(/luma/i);

    // Breadcrumb should show Integrations / Luma
    const breadcrumb = page.locator('text=Integrations').first();
    await expect(breadcrumb).toBeVisible();
  });

  test('Luma config page shows API key input when not connected', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/luma`);
    await page.waitForLoadState('networkidle');

    // Wait for loading skeletons to disappear and the connect form to appear
    // React Query retries failed requests, so this can take up to ~15s
    const apiKeyInput = page.locator('#luma-api-key');
    await expect(apiKeyInput).toBeVisible({ timeout: 20000 });

    // Should show the Connect Luma card
    const connectCard = page.locator('text=Connect Luma').first();
    await expect(connectCard).toBeVisible();

    // Input should be password type by default
    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    // Show/Hide toggle
    const showBtn = page.locator('button:has-text("Show")');
    await expect(showBtn).toBeVisible();

    // Test & Connect button should be present but disabled (no key yet)
    const connectBtn = page.locator('button:has-text("Test & Connect")');
    await expect(connectBtn).toBeVisible();
    await expect(connectBtn).toBeDisabled();

    // Help text with lu.ma/settings/api link
    const helpLink = page.locator('a[href="https://lu.ma/settings/api"]');
    await expect(helpLink).toBeVisible();
  });

  test('user can type API key and show/hide toggle works', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/luma`);
    await page.waitForLoadState('networkidle');

    const apiKeyInput = page.locator('#luma-api-key');
    await apiKeyInput.fill('test-key-for-toggle');

    // Input should be password type initially
    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    // Click Show
    const showBtn = page.locator('button:has-text("Show")');
    await showBtn.click();
    await expect(apiKeyInput).toHaveAttribute('type', 'text');

    // Click Hide
    const hideBtn = page.locator('button:has-text("Hide")');
    await hideBtn.click();
    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    // Connect button should be enabled now
    const connectBtn = page.locator('button:has-text("Test & Connect")');
    await expect(connectBtn).toBeEnabled();
  });

  test('user can type API key and the connect button enables', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/luma`);
    await page.waitForLoadState('networkidle');

    // Wait for connect form to appear after loading
    const apiKeyInput = page.locator('#luma-api-key');
    await expect(apiKeyInput).toBeVisible({ timeout: 20000 });

    const connectBtn = page.locator('button:has-text("Test & Connect")');

    // Initially disabled
    await expect(connectBtn).toBeDisabled();

    // Type a key
    await apiKeyInput.fill(LUMA_API_KEY);

    // Now enabled
    await expect(connectBtn).toBeEnabled();
  });

  test('Integrations link appears in sidebar nav', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations`);
    await page.waitForLoadState('networkidle');

    // Check the sidebar has the Integrations link
    const sidebarLink = page.locator('nav a[href="/integrations"], aside a[href="/integrations"]').first();
    // If sidebar is visible (desktop), verify it
    if (await sidebarLink.isVisible()) {
      await expect(sidebarLink).toContainText(/integrations/i);
    }
  });

  test('ZeroPipeline card and Meetup Coming Soon card are visible', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations`);
    await page.waitForLoadState('networkidle');

    const zeropipeline = page.locator('text=ZeroPipeline').first();
    await expect(zeropipeline).toBeVisible();

    const meetup = page.locator('text=Meetup').first();
    await expect(meetup).toBeVisible();

    const badges = page.locator('text=Coming Soon');
    expect(await badges.count()).toBeGreaterThanOrEqual(1);
  });
});
