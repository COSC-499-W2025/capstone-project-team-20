import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('button', { name: 'Badges' }).click();
  await page.getByRole('button', { name: 'Open Code Cruncher badge' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Open Balanced Palette badge' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Get Yearly Stats (so far)' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Get 2024 Stats' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Open Tiny but Mighty badge' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Open Language Specialist' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Open Rapid Builder badge' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Open Test Pilot badge details' }).click();
  await page.getByRole('button', { name: '✕' }).click();
  await page.getByRole('button', { name: 'Open Test Scout badge details' }).click();
  await page.getByRole('button', { name: '✕' }).click();
});