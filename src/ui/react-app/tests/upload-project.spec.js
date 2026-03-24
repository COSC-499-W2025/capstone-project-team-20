import { test, expect } from '@playwright/test';
// please note, i did select "Apply merges" for this test, so you must rm projects.db for this to pass
// (Apply merges for github usernames only shows on the first time, so fails after first test....)
test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.locator('input[type="file"]').setInputFiles('../../../testResources/testMultiFileAndRepos.zip');
  await page.getByRole('button', { name: 'Apply merges →' }).click();
  await page.getByRole('button', { name: 'Game-Jam-' }).click();
  await page.getByRole('button', { name: 'COSC310-Team-' }).click();
  await page.getByRole('button', { name: 'COSC111' }).click();
  await page.getByRole('button', { name: 'capstone-project-team-' }).click();
  await page.getByRole('button', { name: 'testMultiFileAndRepos' }).click();
});