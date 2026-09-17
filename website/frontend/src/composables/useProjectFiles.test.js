import { ref } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useProjectFiles } from './useProjectFiles';

const git = vi.hoisted(() => ({ listProjectFiles: vi.fn() }));
const stores = vi.hoisted(() => ({
  effective: {
    effectiveStandards: {},
    fetchEffectiveStandards: vi.fn(),
  },
  naming: {
    standards: [],
    fetchStandardsAndComponentNames: vi.fn(),
  },
}));
vi.mock('@/api/service/gitService', () => ({ default: git }));
vi.mock('@/stores/effectiveStandard', () => ({
  useEffectiveStandardStore: () => stores.effective,
}));
vi.mock('@/stores/namingStandard', () => ({
  useNamingStandardStore: () => stores.naming,
}));
vi.mock('@/utils/filenameFromMediaFile', () => ({
  getMediaStandardForProject: vi.fn().mockResolvedValue(null),
}));
vi.mock('@/utils/filenameCompliance', () => ({
  isFilenameCompliant: (_standard, name) => name.startsWith('ok'),
}));

const project = { project_id: 4, project_name: 'corpus' };

describe('useProjectFiles', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    git.listProjectFiles.mockResolvedValue({
      files: [
        { elan_id: 1, name: 'ok-a.eaf' },
        { elan_id: 2, name: 'bad.eaf' },
      ],
    });
    stores.effective.effectiveStandards = { 1: { eaf: 7 } };
    stores.naming.standards = [{ id: 7, name: 'Standard' }];
  });

  it('marks non-compliant files for administrators', async () => {
    const files = useProjectFiles({ isAdmin: ref(true) });
    await files.load(project);

    expect(files.hasEffectiveStandard.value).toBe(true);
    expect(files.nonCompliantFiles.value.map((f) => f.elan_id)).toEqual([2]);

    files.applyRenames([{ elan_id: 2, new_filename: 'ok-b.eaf' }]);
    expect(files.nonCompliantFiles.value).toEqual([]);
    expect(files.files.value[1].name).toBe('ok-b.eaf');
  });

  it('does not check compliance for other users', async () => {
    const files = useProjectFiles({ isAdmin: ref(false) });
    await files.load(project);
    expect(files.files.value.every((file) => file.isCompliant)).toBe(true);
    expect(files.nonCompliantFiles.value).toEqual([]);
  });

  it('discards files of a project the page has left', async () => {
    let resolve;
    git.listProjectFiles.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done;
      })
    );
    const files = useProjectFiles({ isAdmin: ref(true) });
    const stale = files.load(project);
    files.clear();
    resolve({ files: [{ elan_id: 9, name: 'stale.eaf' }] });
    await stale;

    expect(files.files.value).toEqual([]);
    expect(files.loading.value).toBe(false);
  });
});
