import { describe, expect, it } from 'vitest';
import {
  hasProjectCapability,
  hasProjectPermission,
  isInstitutionAdmin,
} from './authorization';

describe('authorization helpers', () => {
  it('lets institution administrators manage every project', () => {
    const admin = { role: 'admin' };
    expect(isInstitutionAdmin(admin)).toBe(true);
    expect(hasProjectPermission(admin, { permission: null }, 'admin')).toBe(
      true
    );
    expect(hasProjectPermission(admin, null, 'admin')).toBe(false);
  });

  it('enforces the read, write, admin hierarchy for researchers', () => {
    const researcher = { role: 'public' };
    expect(
      hasProjectPermission(researcher, { permission: 'write' }, 'read')
    ).toBe(true);
    expect(
      hasProjectPermission(researcher, { permission: 'write' }, 'write')
    ).toBe(true);
    expect(
      hasProjectPermission(researcher, { permission: 'write' }, 'admin')
    ).toBe(false);
    expect(hasProjectPermission(researcher, null, 'read')).toBe(false);
  });

  it('keeps delegated capabilities independent from write permission', () => {
    const researcher = { role: 'public' };
    const project = {
      permission: 'read',
      capabilities: ['manage_protocols'],
    };
    expect(hasProjectCapability(researcher, project, 'manage_protocols')).toBe(
      true
    );
    expect(hasProjectPermission(researcher, project, 'write')).toBe(false);
  });
});
