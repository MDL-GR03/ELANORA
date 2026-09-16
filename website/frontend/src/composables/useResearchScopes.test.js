import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useResearchScopes } from './useResearchScopes';

const api = vi.hoisted(() => ({
  fetchSectionsAndGroups: vi.fn(),
  fetchResearchTopics: vi.fn(),
  fetchProjectBaselineTiers: vi.fn(),
}));
vi.mock('@/api/service/tierService', () => api);

const translate = (key) => `t:${key}`;

describe('useResearchScopes', () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.fetchSectionsAndGroups.mockResolvedValue({ tier_groups: [{ id: 1 }] });
    api.fetchResearchTopics.mockResolvedValue([{ topic_id: 3 }]);
    api.fetchProjectBaselineTiers.mockResolvedValue({ tier_names: ['Role'] });
  });

  it('loads files, topics and baseline tiers', async () => {
    const scopes = useResearchScopes({ translate });
    expect(await scopes.load(4)).toBe(true);
    expect(scopes.tierGroups.value).toEqual([{ id: 1 }]);
    expect(scopes.topics.value).toEqual([{ topic_id: 3 }]);
    expect(scopes.baselineTiers.value).toEqual(['Role']);
    expect(scopes.loading.value).toBe(false);
  });

  it('keeps the files usable when topics cannot be loaded', async () => {
    api.fetchResearchTopics.mockRejectedValue(new Error('down'));
    api.fetchProjectBaselineTiers.mockRejectedValue(new Error('down'));
    const scopes = useResearchScopes({ translate });

    expect(await scopes.load(4)).toBe(true);
    expect(scopes.topics.value).toEqual([]);
    expect(scopes.baselineTiers.value).toEqual([]);
    expect(scopes.topicLoadError.value).toBe(
      't:researchScopes.messages.topicsUnavailable'
    );
  });

  it('reports a failure when the files cannot be loaded', async () => {
    api.fetchSectionsAndGroups.mockRejectedValue(new Error('down'));
    const scopes = useResearchScopes({ translate });

    expect(await scopes.load(4)).toBe(false);
    expect(scopes.error.value).toBe('t:researchScopes.messages.loadFailed');
    expect(scopes.loading.value).toBe(false);
  });

  it('asks for a project when none is selected', async () => {
    const scopes = useResearchScopes({ translate });
    expect(await scopes.load(undefined)).toBe(false);
    expect(scopes.error.value).toBe('t:researchScopes.messages.selectProject');
    expect(api.fetchSectionsAndGroups).not.toHaveBeenCalled();
  });
});
