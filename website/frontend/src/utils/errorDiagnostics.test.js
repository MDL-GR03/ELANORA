import { describe, expect, it, vi } from 'vitest';

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
});
