// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { useProjectStore } from '@/stores/project';
import TiersPage from './TiersPage.vue';

const fetchSectionsAndGroups = vi.fn();

vi.mock('@unhead/vue', () => ({ useHead: vi.fn() }));
vi.mock('@/api/service/tierService', () => ({
  createSection: vi.fn(),
  deleteSection: vi.fn(),
  fetchSectionsAndGroups: (...args) => fetchSectionsAndGroups(...args),
  exportTierSubset: vi.fn(),
  moveTierGroup: vi.fn(),
  renameSection: vi.fn(),
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
        TierGroupRow: true,
        draggable: { template: '<div><slot name="footer" /></div>' },
      },
    },
  });
}

describe('TiersPage project synchronization', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    fetchSectionsAndGroups.mockReset();
  });

  it('reloads for the global project and ignores a stale prior response', async () => {
    const firstRequest = deferred();
    fetchSectionsAndGroups.mockImplementation((projectId) =>
      projectId === 1
        ? firstRequest.promise
        : Promise.resolve({
            sections: [{ section_id: 22, name: 'LSFB corpus' }],
            tier_groups: [],
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
    expect(wrapper.get('[data-testid="project-context"]').text()).toBe('lsfb');
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Organize project files'))
      .trigger('click');
    expect(wrapper.text()).toContain('LSFB corpus');

    firstRequest.resolve({
      sections: [{ section_id: 11, name: 'Stale frapé corpus' }],
      tier_groups: [],
    });
    await flushPromises();

    expect(wrapper.text()).toContain('LSFB corpus');
    expect(wrapper.text()).not.toContain('Stale frapé corpus');
  });
});
