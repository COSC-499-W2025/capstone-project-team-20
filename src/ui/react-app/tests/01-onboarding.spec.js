import { test, expect } from '@playwright/test';

// Please note, config.db must be removed in order for this to pass
// onboarding only runs the first time, so if config.db is still there, it will not access 
// the onboarding page, as it will go directly to the project analyzer
// causing the fail.

test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('button', { name: 'Let\'s get started' }).click();
  await page.getByRole('textbox', { name: 'Full namerequired' }).click();
  await page.getByRole('textbox', { name: 'Full namerequired' }).fill('branden kennedy');
  await page.getByRole('textbox', { name: 'Emailrequired' }).click();
  await page.getByRole('textbox', { name: 'Emailrequired' }).fill('bk@gmail.com');
  await page.getByRole('textbox', { name: 'Phonerequired' }).click();
  await page.getByRole('textbox', { name: 'Phonerequired' }).fill('778-333-4343');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('textbox', { name: 'GitHub username' }).click();
  await page.getByRole('textbox', { name: 'GitHub username' }).fill('branden6');
  await page.getByRole('textbox', { name: 'LinkedIn handle' }).click();
  await page.getByRole('textbox', { name: 'LinkedIn handle' }).fill('brandenkennedy');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await page.getByRole('button', { name: 'Grant consent' }).click();
  await page.getByRole('button', { name: 'Go to Projects' }).click();
});