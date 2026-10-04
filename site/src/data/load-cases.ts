import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parseCaseFiles, type CaseFile } from './case';
import { fixtureCase } from './fixture';

const REPO_CASES_DIR = resolve(process.cwd(), '../presentation/cases');

export const includeFixtures = process.env.CANTHERIA_INCLUDE_FIXTURES === '1';

export function loadCasesFromDirectory(
  directory: string,
  withFixture = false
): CaseFile[] {
  const inputs: Array<{ source: string; data: unknown }> = [];
  if (existsSync(directory)) {
    for (const file of readdirSync(directory).filter((f) => f.endsWith('.json')).sort()) {
      inputs.push({
        source: join(directory, file),
        data: JSON.parse(readFileSync(join(directory, file), 'utf8')) as unknown,
      });
    }
  }
  const reviewed = parseCaseFiles(inputs).filter((c) => c.publication === 'reviewed');
  if (!withFixture) return reviewed;
  return parseCaseFiles([
    ...reviewed.map((c) => ({ source: c.id, data: c })),
    { source: 'src/data/fixture.ts', data: fixtureCase },
  ]);
}

export function loadCases(): CaseFile[] {
  return loadCasesFromDirectory(REPO_CASES_DIR, includeFixtures);
}
