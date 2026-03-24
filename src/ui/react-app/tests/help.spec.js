import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('button', { name: 'Help' }).click();
  await page.getByRole('button', { name: 'Overview ▼' }).click();
  await page.getByRole('button', { name: 'Uploading a Project ▼' }).click();
  await page.getByRole('button', { name: 'Running an Analysis ▼' }).click();
  await page.getByRole('button', { name: 'Understanding Results ▼' }).click();
  await page.getByRole('button', { name: 'Badges ▼' }).click();
  await page.getByRole('button', { name: 'Troubleshooting ▼' }).click();
  await page.getByRole('button', { name: 'Privacy & Security ▼' }).click();
  await page.getByRole('button', { name: 'Privacy & Security ▲' }).click();
  await page.getByRole('button', { name: 'Troubleshooting ▲' }).click();
  await page.getByRole('button', { name: 'Badges ▲' }).click();
  await page.getByRole('button', { name: 'Understanding Results ▲' }).click();
  await page.getByRole('button', { name: 'Running an Analysis ▲' }).click();
  await page.getByRole('button', { name: 'Uploading a Project ▲' }).click();
  await page.getByRole('button', { name: 'Overview ▲' }).click();
});