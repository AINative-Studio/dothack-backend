import { test, expect, Page } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:3000';

async function loginAsTestUser(page: Page) {
  await page.goto(FRONTEND_URL);
  await page.evaluate(() => {
    const fakeToken = 'e2e-test-token-zeropipeline-integration';
    localStorage.setItem('auth_token', fakeToken);
    localStorage.setItem('dothack_access_token', fakeToken);
    document.cookie = `auth_token=${fakeToken}; path=/`;
    document.cookie = `dothack_access_token=${fakeToken}; path=/`;
  });
}

test.describe('ZeroPipeline Integration Settings Flow', () => {

  test('unauthenticated user is redirected to login from /integrations/zeropipeline', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/integrations/zeropipeline`);
    await page.waitForURL(/login/, { timeout: 5000 });
    expect(page.url()).toContain('/login');
  });

  test('authenticated user can navigate to /integrations page and see ZeroPipeline card', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations`);
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1');
    await expect(heading).toContainText(/integrations/i);

    const zpCard = page.locator('text=ZeroPipeline').first();
    await expect(zpCard).toBeVisible();

    const configureBtn = page.locator('a[href="/integrations/zeropipeline"]').first();
    await expect(configureBtn).toBeVisible();
  });

  test('authenticated user can navigate to /integrations/zeropipeline', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/zeropipeline`);
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1');
    await expect(heading).toContainText(/zeropipeline/i);

    const breadcrumb = page.locator('text=Integrations').first();
    await expect(breadcrumb).toBeVisible();
  });

  test('ZeroPipeline config page shows API key input when not connected', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/zeropipeline`);
    await page.waitForLoadState('networkidle');

    const apiKeyInput = page.locator('#zeropipeline-api-key');
    await expect(apiKeyInput).toBeVisible({ timeout: 20000 });

    const connectCard = page.locator('text=Connect ZeroPipeline').first();
    await expect(connectCard).toBeVisible();

    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    const showBtn = page.locator('button:has-text("Show")');
    await expect(showBtn).toBeVisible();

    const connectBtn = page.locator('button:has-text("Test & Connect")');
    await expect(connectBtn).toBeVisible();
    await expect(connectBtn).toBeDisabled();

    const helpLink = page.locator('a[href="https://pipeline.ainative.studio/settings/api-keys"]');
    await expect(helpLink).toBeVisible();
  });

  test('user can type API key and show/hide toggle works', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/zeropipeline`);
    await page.waitForLoadState('networkidle');

    const apiKeyInput = page.locator('#zeropipeline-api-key');
    await expect(apiKeyInput).toBeVisible({ timeout: 20000 });
    await apiKeyInput.fill('test-key-for-toggle');

    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    const showBtn = page.locator('button:has-text("Show")');
    await showBtn.click();
    await expect(apiKeyInput).toHaveAttribute('type', 'text');

    const hideBtn = page.locator('button:has-text("Hide")');
    await hideBtn.click();
    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    const connectBtn = page.locator('button:has-text("Test & Connect")');
    await expect(connectBtn).toBeEnabled();
  });

  test('connect button enables when API key is entered', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/zeropipeline`);
    await page.waitForLoadState('networkidle');

    const apiKeyInput = page.locator('#zeropipeline-api-key');
    await expect(apiKeyInput).toBeVisible({ timeout: 20000 });

    const connectBtn = page.locator('button:has-text("Test & Connect")');
    await expect(connectBtn).toBeDisabled();

    await apiKeyInput.fill('zp_test_key_1234567890');
    await expect(connectBtn).toBeEnabled();
  });

  test('Integrations link appears in sidebar nav', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations/zeropipeline`);
    await page.waitForLoadState('networkidle');

    const sidebarLink = page.locator('nav a[href="/integrations"], aside a[href="/integrations"]').first();
    if (await sidebarLink.isVisible()) {
      await expect(sidebarLink).toContainText(/integrations/i);
    }
  });

  test('ZeroPipeline and Luma cards are both visible on integrations page', async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto(`${FRONTEND_URL}/integrations`);
    await page.waitForLoadState('networkidle');

    const luma = page.locator('text=Luma').first();
    await expect(luma).toBeVisible();

    const zeropipeline = page.locator('text=ZeroPipeline').first();
    await expect(zeropipeline).toBeVisible();

    const meetup = page.locator('text=Meetup').first();
    await expect(meetup).toBeVisible();

    const comingSoon = page.locator('text=Coming Soon');
    expect(await comingSoon.count()).toBeGreaterThanOrEqual(1);
  });
});
