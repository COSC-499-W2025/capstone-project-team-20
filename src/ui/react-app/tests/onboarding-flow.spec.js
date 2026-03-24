import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('button', { name: 'Let\'s get started' }).click();
  await page.getByRole('textbox', { name: 'Full namerequired' }).click();
  await page.getByRole('textbox', { name: 'Full namerequired' }).fill('Branden Kennedy');
  await page.getByRole('textbox', { name: 'Full namerequired' }).press('Tab');
  await page.getByRole('textbox', { name: 'Emailrequired' }).fill('bk@gmail.com');
  await page.getByRole('textbox', { name: 'Emailrequired' }).press('Tab');
  await page.getByRole('textbox', { name: 'Phonerequired' }).fill('778-333-4444');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('textbox', { name: 'GitHub username' }).click();
  await page.getByRole('textbox', { name: 'GitHub username' }).fill('branden6');
  await page.getByRole('textbox', { name: 'LinkedIn handle' }).click();
  await page.getByRole('textbox', { name: 'LinkedIn handle' }).fill('brandenkennedy');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await page.getByRole('button', { name: 'Grant consent' }).click();
  await page.getByRole('button', { name: 'Go to Projects' }).click();
});