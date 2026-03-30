import { test, expect } from '@playwright/test';

test('portfolio create/edit/export', async ({ page, context }) => {
  test.setTimeout(60000);

  await page.goto('http://localhost:5173/');

  await page.getByRole('button', { name: 'Portfolio' }).click();

  const nameInput = page.locator('input[type="text"]');
  await nameInput.click();
  await nameInput.fill('Test portfolio playwright');

  await page.getByRole('button', { name: 'Create Portfolio Report' }).click();
  await page.getByRole('button', { name: 'Generate Web Portfolio' }).click();

  await page.getByRole('article').nth(1).click();

  const expandBtn = page.getByRole('button', { name: '▸ Expand' }).first();
  await expandBtn.click();
  await expandBtn.click();

  const titleBox = page.getByRole('textbox', { name: 'Custom title COSC310-Team-' });

  await titleBox.fill('Pogodo (COSC 310)');
  await titleBox.press('Enter');

  await page.getByRole('button', { name: 'Save Changes' }).nth(2).click();

  const overviewBox = page.getByRole('textbox', { name: 'Custom overview Game-Jam-' });
  await overviewBox.fill('We created a game in Unity for the Global Game Jam 2025!');

  await page.getByRole('button', { name: 'Save Changes' }).nth(3).click();

// Trigger export and verify backend export endpoint succeeds
  const exportResponsePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes('/portfolio/exports/') &&
      resp.request().method() === 'GET' &&
      resp.status() === 200
  );

  await page.getByRole('button', { name: 'Export Portfolio PDF' }).click();
  await exportResponsePromise;

// Support both behaviors: popup tab OR same-tab navigation
  const popup = await context.waitForEvent('page', { timeout: 5000 }).catch(() => null);

  if (popup) {
    await popup.waitForLoadState('domcontentloaded');
    await expect(popup).toHaveURL(/\/portfolio\/exports\//);
  } else {
    await expect(page).toHaveURL(/\/portfolio\/exports\//);
  }
  await newPage.waitForLoadState('domcontentloaded');

  const url = newPage.url();
  expect(url).toContain('/portfolio/exports/');
});
