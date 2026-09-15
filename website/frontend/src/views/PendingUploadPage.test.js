// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { reactive } from 'vue';
import { createI18n } from 'vue-i18n';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import PendingUploadPage from './PendingUploadPage.vue';

const route = reactive({ query: {} });
const router = {
  replace: vi.fn(async ({ query }) => {
    route.query = query;
  }),
};

const getPendingUploadsWithStatus = vi.fn();
const declinePendingUpload = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => router,
}));
vi.mock('@/api/service/gitService', () => ({
  default: {
    getPendingUploadsWithStatus: (...args) =>
      getPendingUploadsWithStatus(...args),
    declinePendingUpload: (...args) => declinePendingUpload(...args),
    adminTestMerge: vi.fn(),
    adminCompleteMerge: vi.fn(),
    dismissDuplicateUpload: vi.fn(),
    setContributionResearchTopic: vi.fn(),
  },
}));
vi.mock('@/api/service/reviewService', () => ({
  default: { list: vi.fn().mockResolvedValue([]) },
}));
vi.mock('@/api/service/tierService', () => ({
  fetchResearchTopics: vi.fn().mockResolvedValue([]),
}));

function upload(id) {
  return {
    upload_id: id,
    merge_status: 'ready_to_merge',
    uploaded_by: `researcher-${id}`,
    files: { new: [], modified: [`elan_files/session-${id}.eaf`], deleted: [] },
    semantic_summary: {},
    research_context: {},
  };
}

const CardHeader = {
  name: 'ContributionCardHeader',
  props: ['upload'],
  emits: ['decline', 'view'],
  template: `<div class="card" :data-upload="upload.upload_id">
      <button class="card-view" @click="$emit('view')">view</button>
      <button class="card-decline" @click="$emit('decline')">decline</button>
    </div>`,
};

function mountPage() {
  return mount(PendingUploadPage, {
    global: {
      plugins: [
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
      stubs: {
        FontAwesomeIcon: true,
        'font-awesome-icon': true,
        'router-link': true,
        WorkspaceHeader: true,
        ReviewCasePanel: true,
        UploadResolutionView: true,
        AcceptedProjectHistory: true,
        ContributionCardBody: true,
        ContributionResearchContext: true,
        ContributionCardHeader: CardHeader,
        UploadDetailsView: {
          props: ['upload'],
          template:
            '<div class="details-workspace">details {{ upload.upload_id }}</div>',
        },
      },
    },
    attachTo: document.body,
  });
}

describe('PendingUploadPage', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    route.query = {};
    router.replace.mockClear();
    declinePendingUpload.mockReset().mockResolvedValue({});
    getPendingUploadsWithStatus
      .mockReset()
      .mockResolvedValue({ pending_uploads: [upload(5), upload(7)] });
    useUserStore().user = { user_id: 1, role: 'admin' };
    useProjectStore().setCurrentProject({
      project_id: 1,
      project_name: 'corpus',
      permission: 'admin',
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  it('declines exactly the contribution whose button was pressed', async () => {
    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('.card[data-upload="7"] .card-decline').trigger('click');
    expect(wrapper.text()).toContain('Contribution #7');
    expect(wrapper.text()).toContain('Decline contribution');

    await wrapper.get('textarea').setValue('Outside the declared scope');
    await wrapper.get('form.decline-modal').trigger('submit');
    await flushPromises();

    expect(declinePendingUpload).toHaveBeenCalledWith(
      'corpus',
      7,
      'Outside the declared scope'
    );
    expect(wrapper.find('form.decline-modal').exists()).toBe(false);
    wrapper.unmount();
  });

  it('closes a workspace whose contribution stopped being pending', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    });
    route.query = { view: 'queue', workspace: 'details', upload: '5' };
    const wrapper = mountPage();
    await flushPromises();
    expect(wrapper.get('.details-workspace').text()).toContain('5');

    // Another administrator accepted #5 before the next automatic refresh.
    getPendingUploadsWithStatus.mockResolvedValue({
      pending_uploads: [upload(7)],
    });
    await vi.advanceTimersByTimeAsync(30000);
    await flushPromises();

    expect(route.query.workspace).toBeUndefined();
    expect(wrapper.find('.details-workspace').exists()).toBe(false);
    expect(wrapper.find('[role="tablist"]').exists()).toBe(true);
    expect(
      useEventMessageStore().messages.map((message) => message.translationKey)
    ).toContain('contributionWorkspace.messages.noLongerPending');
    wrapper.unmount();
  });

  it('translates the message shown when no contribution matches a filter', async () => {
    const wrapper = mountPage();
    await flushPromises();

    await wrapper
      .findComponent({ name: 'ContributionQueueControls' })
      .vm.$emit('update:query', 'nothing matches this');
    await flushPromises();

    expect(wrapper.text()).toContain(
      messages.contributionWorkspace.queue.noMatches
    );
    wrapper.unmount();
  });
});
