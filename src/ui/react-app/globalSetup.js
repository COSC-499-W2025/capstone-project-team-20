import { rm } from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

export default async function globalSetup() {
  for (const db of ['config.db', 'projects.db', 'reports.db']) {
    await rm(path.join(projectRoot, db), { force: true });
  }
}
