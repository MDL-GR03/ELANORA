// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { useProjectStore } from '@/stores/project';
import TiersPage from './TiersPage.vue';

const fetchSectionsAndGroups = vi.fn();
const fetchResearchTopics = vi.fn();
const fetchProjectBaselineTiers = vi.fn();

vi.mock('@unhead/vue', () => ({ useHead: vi.fn() }));
vi.mock('@/api/service/tierService', () => ({
  createResearchTopic: vi.fn(),
  deleteResearchTopic: vi.fn(),
  fetchSectionsAndGroups: (...args) => fetchSectionsAndGroups(...args),
  fetchResearchTopics: (...args) => fetchResearchTopics(...args),
  fetchProjectBaselineTiers: (...args) => fetchProjectBaselineTiers(...args),
  exportTierSubset: vi.fn(),
  updateResearchTopic: vi.fn(),
  updateProjectBaselineTiers: vi.fn(),
}));

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function mountPage(pinia) {
  return mount(TiersPage, {
    global: {
      plugins: [
        pinia,
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
      stubs: {
        FontAwesomeIcon: true,
        WorkspaceHeader: {
          props: ['context'],
          template: '<div data-testid="project-context">{{ context }}</div>',
        },
        TierSelectionTree: true,
      },
    },
  });
}

describe('TiersPage project synchronization', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    fetchSectionsAndGroups.mockReset();
    fetchResearchTopics.mockReset();
    fetchResearchTopics.mockResolvedValue([]);
    fetchProjectBaselineTiers.mockReset();
    fetchProjectBaselineTiers.mockResolvedValue({ tier_names: ['Role1'] });
  });

  it('reloads for the global project and ignores a stale prior response', async () => {
    const firstRequest = deferred();
    fetchSectionsAndGroups.mockImplementation((projectId) =>
      projectId === 1
        ? firstRequest.promise
        : Promise.resolve({
            sections: [],
            tier_groups: [
              { tier_group_id: 22, elan_file_name: 'LSFB.eaf', tiers: [] },
            ],
          })
    );

    const pinia = createPinia();
    setActivePinia(pinia);
    const projectStore = useProjectStore();
    projectStore.setCurrentProject({ project_id: 1, project_name: 'frapé' });
    const wrapper = mountPage(pinia);
    await flushPromises();

    projectStore.setCurrentProject({ project_id: 2, project_name: 'lsfb' });
    await flushPromises();

    expect(fetchSectionsAndGroups).toHaveBeenCalledWith(1);
    expect(fetchSectionsAndGroups).toHaveBeenCalledWith(2);
    expect(fetchProjectBaselineTiers).toHaveBeenCalledWith(1);
    expect(fetchProjectBaselineTiers).toHaveBeenCalledWith(2);
    expect(wrapper.get('[data-testid="project-context"]').text()).toBe('lsfb');
    expect(wrapper.text()).toContain('LSFB.eaf');
    expect(wrapper.text()).toContain('Creates a separate download');
    expect(wrapper.text()).toContain('The shared project file is not changed.');

    firstRequest.resolve({
      sections: [],
      tier_groups: [
        { tier_group_id: 11, elan_file_name: 'Stale.eaf', tiers: [] },
      ],
    });
    await flushPromises();

    expect(wrapper.text()).toContain('LSFB.eaf');
    expect(wrapper.text()).not.toContain('Stale.eaf');

    await wrapper
      .findAll('.tiers-mode-tabs button')
      .find((button) => button.text().includes('Research topics'))
      .trigger('click');
    expect(wrapper.get('.baseline-tier-chips').text()).toContain('Role1');
  });

  it('exposes linked tabs and supports keyboard navigation', async () => {
    fetchSectionsAndGroups.mockResolvedValue({ sections: [], tier_groups: [] });
    const pinia = createPinia();
    setActivePinia(pinia);
    useProjectStore().setCurrentProject({
      project_id: 1,
      project_name: 'Keyboard corpus',
    });
    const wrapper = mountPage(pinia);
    await flushPromises();

    const prepare = wrapper.get('#research-copy-tab');
    const topics = wrapper.get('#research-topics-tab');
    expect(wrapper.get('[role="tablist"]').exists()).toBe(true);
    expect(prepare.attributes('aria-controls')).toBe('research-copy-panel');
    await prepare.trigger('keydown', { key: 'ArrowRight' });
    await wrapper.vm.$nextTick();

    expect(topics.attributes('aria-selected')).toBe('true');
    expect(wrapper.get('#research-topics-panel').attributes('role')).toBe(
      'tabpanel'
    );
  });
});
