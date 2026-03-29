import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import path from 'path';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  workers: 1,
  globalSetup: './globalSetup.js',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    video: 'on',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: 'npm run dev',
      port: 5173,
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
    {
      command: 'python -m uvicorn src.api.api_main:app --port 8000',
      cwd: projectRoot,
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
});
