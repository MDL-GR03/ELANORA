import { describe, expect, it, vi } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { extname, join, relative } from 'node:path';

import { getSafeErrorMetadata, reportClientError } from './errorDiagnostics';

describe('errorDiagnostics', () => {
  it('keeps only bounded operational metadata', () => {
    expect(
      getSafeErrorMetadata({
        code: 'ERR_NETWORK',
        message: 'Request failed for ada@example.test',
        config: { data: { password: 'secret' } },
        response: {
          status: 422,
          data: { detail: 'Invalid token abc-123', email: 'ada@example.test' },
          headers: { authorization: 'Bearer secret' },
        },
      })
    ).toEqual({ status: 422, code: 'ERR_NETWORK' });
  });

  it('never sends the raw exception to the console', () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    const error = {
      message: 'password=secret',
      response: { status: 401, data: { token: 'private-token' } },
    };

    reportClientError('Login failed', error);

    expect(consoleError).toHaveBeenCalledWith('Login failed', { status: 401 });
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain('secret');
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain(
      'private-token'
    );
    consoleError.mockRestore();
  });

  it('keeps production error logging behind the safe diagnostic utility', () => {
    const sourceRoot = join(process.cwd(), 'src');
    const violations = [];

    function inspect(directory) {
      for (const entry of readdirSync(directory, { withFileTypes: true })) {
        const path = join(directory, entry.name);
        if (entry.isDirectory()) {
          inspect(path);
          continue;
        }
        if (
          !['.js', '.vue'].includes(extname(path)) ||
          path.endsWith('.test.js')
        ) {
          continue;
        }
        const source = readFileSync(path, 'utf8');
        const relativePath = relative(sourceRoot, path);
        if (
          relativePath !== 'utils/errorDiagnostics.js' &&
          source.includes('console.error(')
        ) {
          violations.push(`${relativePath}: direct console.error`);
        }
        if (source.includes('console.log(')) {
          violations.push(`${relativePath}: production console.log`);
        }
      }
    }

    inspect(sourceRoot);
    expect(violations).toEqual([]);
  });
});
