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

  await page.getByRole('textbox', { name: /Custom title/ }).fill('Pogodo (COSC 310)');
  await page.getByRole('textbox', { name: /Custom title/ }).press('Enter');

  await page.getByRole('button', { name: 'Save Changes' }).nth(2).click();

  const overviewBox = page.getByRole('textbox', { name: /Custom overview/ });
  await overviewBox.fill('We created a game in Unity for the Global Game Jam 2025!');

  await page.getByRole('button', { name: 'Save Changes' }).nth(3).click();

  const [newPage] = await Promise.all([
    context.waitForEvent('page'),
    page.getByRole('button', { name: 'Export Portfolio PDF' }).click(),
  ]);

  await newPage.waitForLoadState('domcontentloaded');

  const url = newPage.url();
  expect(url).toContain('/portfolio/exports/');
});