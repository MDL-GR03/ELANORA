import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useUploadStandard } from './useUploadStandard';

const stores = vi.hoisted(() => ({
  effective: { effectiveStandards: {}, fetchEffectiveStandards: vi.fn() },
  naming: { standards: [], fetchStandardsAndComponentNames: vi.fn() },
}));
vi.mock('@/stores/effectiveStandard', () => ({
  useEffectiveStandardStore: () => stores.effective,
}));
vi.mock('@/stores/namingStandard', () => ({
  useNamingStandardStore: () => stores.naming,
}));
vi.mock('@/utils/filenameCompliance', () => ({
  isFilenameCompliant: (_standard, name) => name.startsWith('ok'),
}));

describe('useUploadStandard', () => {
  beforeEach(() => {
    stores.effective.fetchEffectiveStandards.mockReset();
    stores.effective.effectiveStandards = { 4: { eaf: 2 } };
    stores.naming.standards = [{ id: 2 }];
  });

  it('checks filenames against the upload standard', async () => {
    const standard = useUploadStandard();
    expect(await standard.load(1)).toBe(true);
    expect(standard.hasStandard.value).toBe(true);
    expect(standard.isCompliant('ok.eaf')).toBe(true);
    expect(standard.isCompliant('bad.eaf')).toBe(false);
  });

  it('accepts any filename when the project has no standard', async () => {
    stores.effective.effectiveStandards = {};
    const standard = useUploadStandard();
    await standard.load(1);
    expect(standard.isCompliant('bad.eaf')).toBe(true);
  });

  it('reports a failure so uploading can pause', async () => {
    stores.effective.fetchEffectiveStandards.mockRejectedValue(new Error('x'));
    const standard = useUploadStandard();
    expect(await standard.load(1)).toBe(false);
    expect(standard.failed.value).toBe(true);
    expect(standard.loading.value).toBe(false);
  });
});
