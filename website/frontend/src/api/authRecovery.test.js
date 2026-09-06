import { describe, expect, it, vi } from 'vitest';

import { createAuthRecovery } from './authRecovery';

describe('createAuthRecovery', () => {
  it('shares one refresh between concurrent unauthorized requests', async () => {
    let finishRefresh;
    const refresh = vi.fn(
      () =>
        new Promise((resolve) => {
          finishRefresh = resolve;
        })
    );
    const onFailure = vi.fn();
    const recovery = createAuthRecovery({ refresh, onFailure });

    const first = recovery.attempt();
    const second = recovery.attempt();
    await Promise.resolve();

    expect(refresh).toHaveBeenCalledTimes(1);
    finishRefresh();
    await expect(Promise.all([first, second])).resolves.toEqual([
      undefined,
      undefined,
    ]);
    expect(onFailure).not.toHaveBeenCalled();
  });

  it('latches a failed refresh so later polling cannot start a request storm', async () => {
    const expired = new Error('refresh token expired');
    const refresh = vi.fn().mockRejectedValue(expired);
    const onFailure = vi.fn();
    const recovery = createAuthRecovery({ refresh, onFailure });

    await expect(recovery.attempt()).rejects.toBe(expired);
    await expect(recovery.attempt()).rejects.toBe(expired);

    expect(refresh).toHaveBeenCalledTimes(1);
    expect(onFailure).toHaveBeenCalledOnce();
  });

  it('allows recovery again after a successful login resets the latch', async () => {
    const refresh = vi
      .fn()
      .mockRejectedValueOnce(new Error('expired'))
      .mockResolvedValueOnce(undefined);
    const recovery = createAuthRecovery({ refresh, onFailure: vi.fn() });

    await expect(recovery.attempt()).rejects.toThrow('expired');
    recovery.reset();
    await expect(recovery.attempt()).resolves.toBeUndefined();

    expect(refresh).toHaveBeenCalledTimes(2);
  });
});
