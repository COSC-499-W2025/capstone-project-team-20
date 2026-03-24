import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('button', { name: 'Portfolio' }).click();
  await page.locator('input[type="text"]').click();
  await page.locator('input[type="text"]').press('ControlOrMeta+a');
  await page.locator('input[type="text"]').fill('Test portfolio playwright');
  await page.getByRole('button', { name: 'Create Portfolio Report' }).click();
  await page.getByRole('button', { name: 'Generate Web Portfolio' }).click();
  await page.getByRole('article').nth(1).click();
  await page.getByRole('button', { name: '▸ Expand' }).first().click();
  await page.getByRole('button', { name: '▸ Expand' }).first().click();
  await page.getByRole('article').filter({ hasText: '▸ Expand' }).click();
  await page.getByRole('textbox', { name: 'Custom title COSC310-Team-' }).click();
  await page.getByRole('textbox', { name: 'Custom title COSC310-Team-' }).fill('Pogodo (COSC 310)');
  await page.getByRole('textbox', { name: 'Custom title COSC310-Team-' }).press('Enter');
  await page.getByRole('button', { name: 'Save Changes' }).nth(2).click();
  await page.getByRole('textbox', { name: 'Custom overview Game-Jam-' }).click();
  await page.getByRole('textbox', { name: 'Custom overview Game-Jam-' }).press('ControlOrMeta+a');
  await page.getByRole('textbox', { name: 'Custom overview Game-Jam-' }).fill('We created a game in Unity for the Global Game Jam 2025!');
  await page.getByRole('button', { name: 'Save Changes' }).nth(3).click();
  const page1Promise = page.waitForEvent('popup');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export Portfolio PDF' }).click();
  const page1 = await page1Promise;
  const download = await downloadPromise;
});