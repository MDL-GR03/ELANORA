// @vitest-environment jsdom

import { defineComponent, h, ref } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { useResearchCopySelection } from '@/composables/useResearchCopySelection';
import ResearchCopyWorkspace from './ResearchCopyWorkspace.vue';
import ResearchTopicEditor from './ResearchTopicEditor.vue';
import ResearchTopicsPanel from './ResearchTopicsPanel.vue';
import TopicCoveragePanel from './TopicCoveragePanel.vue';
import { provideResearchCopyContext } from './researchCopyContext';

const api = vi.hoisted(() => ({
  createResearchTopic: vi.fn(),
  deleteResearchTopic: vi.fn(),
  exportTierSubset: vi.fn(),
  updateResearchTopic: vi.fn(),
  updateProjectBaselineTiers: vi.fn(),
}));
const confirm = vi.hoisted(() => vi.fn());
vi.mock('@/api/service/tierService', () => api);
vi.mock('@/composables/useUserConfirm', () => ({
  useUserConfirm: () => confirm,
}));

const tier = (tier_name, children = []) => ({ tier_name, children });
const tierGroups = [
  {
    tier_group_id: 1,
    elan_file_name: 'a.eaf',
    tiers: [tier('Gloss'), tier('Notes')],
  },
  { tier_group_id: 2, elan_file_name: 'b.eaf', tiers: [tier('Gloss')] },
];
const topic = {
  topic_id: 5,
  name: 'Glossing',
  description: '',
  tier_names: ['Gloss', 'Notes'],
  allow_new_tiers: true,
};

function globalOptions() {
  return {
    plugins: [
      createPinia(),
      createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
    ],
    stubs: { FontAwesomeIcon: true, TierSelectionTree: true },
  };
}

describe('ResearchTopicEditor', () => {
  it('starts from the edited topic and emits the changed payload', async () => {
    const wrapper = mount(ResearchTopicEditor, {
      props: { topic, tierGroups },
      global: globalOptions(),
    });
    await wrapper.get('.topic-fields input').setValue('  Glosses ');
    await wrapper
      .find('.topic-tier-picker input[type="checkbox"]')
      .trigger('change');
    await wrapper.get('form').trigger('submit');

    expect(wrapper.emitted('save')[0][0]).toEqual({
      name: 'Glosses',
      description: null,
      tier_names: ['Notes'],
      allow_new_tiers: true,
    });
  });

  it('cannot be saved without a name and a tier', () => {
    const wrapper = mount(ResearchTopicEditor, {
      props: { tierGroups },
      global: globalOptions(),
    });
    expect(
      wrapper.get('button[type="submit"]').attributes('disabled')
    ).toBeDefined();
  });
});

describe('TopicCoveragePanel', () => {
  it('filters files by name or tier and pages through them', async () => {
    const many = Array.from({ length: 12 }, (_, index) => ({
      tier_group_id: index,
      elan_file_name: `f${String(index).padStart(2, '0')}.eaf`,
      tiers: [tier('Gloss')],
    }));
    const wrapper = mount(TopicCoveragePanel, {
      props: { topic, tierGroups: many },
      global: globalOptions(),
    });
    expect(wrapper.findAll('.topic-file-coverage-row')).toHaveLength(10);
    await wrapper.get('.topic-show-more').trigger('click');
    expect(wrapper.findAll('.topic-file-coverage-row')).toHaveLength(12);

    await wrapper.get('.topic-coverage-search input').setValue('f03');
    expect(wrapper.findAll('.topic-file-coverage-row')).toHaveLength(1);
  });
});

describe('ResearchTopicsPanel', () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    confirm.mockReset();
  });

  function mountPanel() {
    return mount(ResearchTopicsPanel, {
      props: {
        projectId: 9,
        topics: [topic],
        tierGroups,
        baselineTiers: [],
        canManage: true,
      },
      global: globalOptions(),
    });
  }

  it('shows why a topic could not be deleted', async () => {
    confirm.mockResolvedValue(true);
    api.deleteResearchTopic.mockRejectedValue({
      response: { data: { code: 'research_topic_not_found' } },
    });
    const wrapper = mountPanel();

    await wrapper.get('.topic-action-button.is-danger').trigger('click');
    await flushPromises();

    expect(api.deleteResearchTopic).toHaveBeenCalledWith(9, 5);
    expect(wrapper.get('[role="alert"]').text()).toBe(
      messages.apiErrors.research_topic_not_found
    );
    expect(wrapper.emitted('changed')).toBeUndefined();
  });

  it('creates a topic and asks the page to reload', async () => {
    api.createResearchTopic.mockResolvedValue({});
    const wrapper = mountPanel();

    await wrapper.get('.topics-intro button').trigger('click');
    await wrapper.get('.topic-fields input').setValue('Mouthing');
    await wrapper
      .find('.topic-editor .topic-tier-picker input')
      .trigger('change');
    await wrapper.get('.topic-editor').trigger('submit');
    await flushPromises();

    expect(api.createResearchTopic).toHaveBeenCalledWith(9, {
      name: 'Mouthing',
      description: null,
      tier_names: ['Gloss'],
      allow_new_tiers: false,
    });
    expect(wrapper.emitted('changed')).toHaveLength(1);
    expect(wrapper.find('.topic-editor').exists()).toBe(false);
  });
});

describe('ResearchCopyWorkspace', () => {
  it('downloads the selected file with the chosen tiers', async () => {
    api.exportTierSubset.mockResolvedValue({ data: new Blob(['x']) });
    URL.createObjectURL = vi.fn(() => 'blob:x');
    URL.revokeObjectURL = vi.fn();
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    const Host = defineComponent({
      setup() {
        const groups = ref(tierGroups);
        const topics = ref([topic]);
        const selection = useResearchCopySelection({
          tierGroups: groups,
          topics,
          baselineTiers: ref([]),
        });
        provideResearchCopyContext({
          ...selection,
          tierGroups: groups,
          topics,
        });
        selection.applyTopic(topic);
        return () => h(ResearchCopyWorkspace, { projectName: 'corpus' });
      },
    });
    const wrapper = mount(Host, { global: globalOptions() });

    await wrapper.get('.tier-export-footer button').trigger('click');
    await flushPromises();

    expect(api.exportTierSubset).toHaveBeenCalledWith(
      'corpus',
      'a.eaf',
      ['Gloss', 'Notes'],
      5,
      [],
      []
    );
    expect(click).toHaveBeenCalledOnce();
  });
});
