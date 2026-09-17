// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import UploadPage from './UploadPage.vue';

const git = vi.hoisted(() => ({ uploadElanFiles: vi.fn() }));
const reviews = vi.hoisted(() => ({ list: vi.fn(), resubmit: vi.fn() }));
const route = vi.hoisted(() => ({ query: {} }));
vi.mock('@/api/service/gitService', () => ({ default: git }));
vi.mock('@/api/service/reviewService', () => ({ default: reviews }));
vi.mock('@/api/service/tierService', () => ({
  fetchResearchTopics: vi
    .fn()
    .mockResolvedValue([{ topic_id: 3, name: 'Mouthing' }]),
}));
vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock('@/composables/useUploadStandard', async () => {
  const { ref, computed } = await import('vue');
  return {
    useUploadStandard: () => ({
      loading: ref(false),
      failed: ref(false),
      hasStandard: computed(() => false),
      load: vi.fn().mockResolvedValue(true),
      clear: vi.fn(),
      isCompliant: () => true,
    }),
  };
});
vi.mock('@/utils/researchExtract', () => ({
  detectResearchScope: vi.fn().mockResolvedValue(null),
}));

const file = { name: 'session.eaf' };
const UploadFolderStub = {
  emits: ['update:modelValue'],
  data: () => ({ files: [file] }),
  template:
    '<button class="pick-files" @click="$emit(\'update:modelValue\', files)">pick</button>',
};
const AppSelectStub = {
  props: { modelValue: { type: [String, Number], default: '' } },
  emits: ['update:modelValue'],
  template:
    '<button class="app-select" :data-value="modelValue" @click="$emit(\'update:modelValue\', \'3\')">select</button>',
};

function mountPage() {
  const projects = useProjectStore();
  projects.initializeFromStorage = vi.fn();
  projects.ensureProjects = vi.fn();
  projects.initBroadcastChannel = vi.fn();
  projects.setProjects([{ project_id: 7, project_name: 'Corpus' }]);
  useUserStore().user = { username: 'ada' };
  return mount(UploadPage, {
    global: {
      plugins: [
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
      stubs: {
        FontAwesomeIcon: true,
        WorkspaceHeader: true,
        RouterLink: true,
        UploadFolder: UploadFolderStub,
        AppSelect: AppSelectStub,
      },
    },
  });
}

describe('UploadPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    git.uploadElanFiles.mockReset();
    route.query = { project: '7' };
  });

  it('submits files with their research topic and summary', async () => {
    git.uploadElanFiles.mockResolvedValue({
      upload_id: 11,
      uploaded_files: [{ filename: 'session.eaf' }],
      failed_files: [],
    });
    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('.pick-files').trigger('click');
    await flushPromises();
    await wrapper.get('#upload-research-topic').trigger('click');
    await wrapper.get('textarea').setValue('Corrected glosses');
    await wrapper.get('.upload-btn').trigger('click');
    await flushPromises();

    expect(git.uploadElanFiles).toHaveBeenCalledWith(7, [file], 'ada', null, {
      topicId: 3,
      proposedTopicName: '',
      summary: 'Corrected glosses',
    });
    expect(wrapper.get('.upload-results').text()).toContain('session.eaf');
    expect(wrapper.find('textarea').exists()).toBe(false);
  });

  it('keeps the upload closed until every requested correction file is added', async () => {
    route.query = { project: '7', correction: 'case-1' };
    reviews.list.mockResolvedValue([
      {
        case_id: 'case-1',
        state: 'changes_requested',
        title: 'Fix glosses',
        tasks: [
          {
            task_id: 1,
            filename: 'other.eaf',
            status: 'open',
            instruction: '',
          },
        ],
      },
    ]);
    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get('.pick-files').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('other.eaf');
    expect(wrapper.get('.upload-btn').attributes('disabled')).toBeDefined();
  });
});
