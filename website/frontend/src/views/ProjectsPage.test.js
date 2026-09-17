// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import ProjectsPage from './ProjectsPage.vue';

const git = vi.hoisted(() => ({
  deleteProject: vi.fn(),
  listProjectFiles: vi.fn(),
  listUserProjects: vi.fn(),
}));
vi.mock('@/api/service/gitService', () => ({ default: git }));
vi.mock('@unhead/vue', () => ({ useHead: vi.fn() }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('@/composables/useUserConfirm', () => ({
  useUserConfirm: () => vi.fn().mockResolvedValue(true),
}));
vi.mock('@/composables/useProjectFiles', async () => {
  const { ref, computed } = await import('vue');
  return {
    useProjectFiles: () => ({
      files: ref([]),
      loading: ref(false),
      projectStandard: ref(null),
      mediaStandard: ref(null),
      hasEffectiveStandard: computed(() => false),
      checksCompliance: computed(() => false),
      nonCompliantFiles: computed(() => []),
      load: vi.fn(),
      clear: vi.fn(),
      applyRenames: vi.fn(),
    }),
  };
});

const project = { project_id: 1, project_name: 'Corpus', permission: 'owner' };

describe('ProjectsPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    Object.values(git).forEach((mock) => mock.mockReset());
  });

  it('tells an administrator why a project could not be deleted', async () => {
    git.deleteProject.mockRejectedValue({
      response: { data: { code: 'project_locked' } },
    });
    const projects = useProjectStore();
    projects.initialized = true;
    projects.initBroadcastChannel = vi.fn();
    projects.loadCurrentProject = vi.fn();
    projects.setProjects([project]);
    useUserStore().user = { user_id: 1, role: 'admin' };
    const events = useEventMessageStore();
    events.addMessage = vi.fn();

    const wrapper = mount(ProjectsPage, {
      global: {
        plugins: [
          createI18n({
            legacy: false,
            locale: 'en',
            messages: { en: messages },
          }),
        ],
        stubs: {
          FontAwesomeIcon: true,
          WorkspaceHeader: true,
          FileTree: true,
          ProjectSyncDialog: true,
        },
      },
    });
    await flushPromises();
    await wrapper.get('.project-card-delete-btn').trigger('click');
    await flushPromises();

    expect(git.deleteProject).toHaveBeenCalledWith('Corpus');
    expect(events.addMessage).toHaveBeenCalledWith(
      messages.apiErrors.project_locked,
      'error'
    );
  });
});
