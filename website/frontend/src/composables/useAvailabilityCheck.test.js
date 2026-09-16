import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AVAILABILITY_CHECK_DELAY,
  useAvailabilityCheck,
} from './useAvailabilityCheck';

function createCheck(overrides = {}) {
  const check = vi
    .fn()
    .mockResolvedValue({ available: true, message: 'free to use' });
  const reportError = vi.fn();
  const availability = useAvailabilityCheck({
    check,
    translate: (key) => key,
    errorKey: 'register.username_check_error',
    minimumLength: 3,
    reportError,
    ...overrides,
  });
  return { check, reportError, availability };
}

describe('useAvailabilityCheck', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('asks once typing stops and keeps the answer', async () => {
    const { check, availability } = createCheck();
    availability.request('ada');
    expect(availability.checking.value).toBe(true);
    expect(check).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY);
    expect(check).toHaveBeenCalledWith('ada');
    expect(availability.available.value).toBe(true);
    expect(availability.message.value).toBe('free to use');
    expect(availability.checking.value).toBe(false);
  });

  it('drops a pending request when the value changes again', async () => {
    const { check, availability } = createCheck();
    availability.request('ada');
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY / 2);
    availability.request('adal');
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY);
    expect(check).toHaveBeenCalledTimes(1);
    expect(check).toHaveBeenCalledWith('adal');
  });

  it('does not ask about a value too short to be accepted', async () => {
    const { check, availability } = createCheck();
    availability.request('ad');
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY);
    expect(check).not.toHaveBeenCalled();
    expect(availability.checking.value).toBe(false);
  });

  it('does not ask while the field fails its own rules', async () => {
    const { check, availability } = createCheck();
    availability.request('ada lovelace', { skip: true });
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY);
    expect(check).not.toHaveBeenCalled();
  });

  it('leaves the answer unknown when the check fails', async () => {
    const { check, reportError, availability } = createCheck();
    check.mockRejectedValue(new Error('offline'));
    availability.request('ada');
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY);
    expect(availability.available.value).toBeNull();
    expect(availability.message.value).toBe('register.username_check_error');
    expect(availability.checking.value).toBe(false);
    expect(reportError).toHaveBeenCalled();
  });

  it('reports a value already taken', async () => {
    const { check, availability } = createCheck();
    check.mockResolvedValue({ available: false, message: 'already taken' });
    availability.request('ada');
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY);
    expect(availability.available.value).toBe(false);
    expect(availability.message.value).toBe('already taken');
  });

  it('forgets the answer on reset', async () => {
    const { availability } = createCheck();
    availability.request('ada');
    await vi.advanceTimersByTimeAsync(AVAILABILITY_CHECK_DELAY);
    availability.reset();
    expect(availability.available.value).toBeNull();
    expect(availability.message.value).toBe('');
  });
});
