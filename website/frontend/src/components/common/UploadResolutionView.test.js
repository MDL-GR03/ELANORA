// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import en from '@/locales/en.json';
import fr from '@/locales/fr.json';
import UploadResolutionView from './UploadResolutionView.vue';

const adminCompleteMerge = vi.fn();

vi.mock('@/api/service/gitService', () => ({
  default: { adminCompleteMerge: (...args) => adminCompleteMerge(...args) },
}));
vi.mock('@/utils/errorDiagnostics', () => ({ reportClientError: vi.fn() }));

function contribution(id = 5) {
  return {
    upload_id: id,
    branch_name: `contribution-${id}_pending_approval`,
    conflicted_files: ['elan_files/a.eaf', 'elan_files/b.eaf'],
    files: {
      new: ['elan_files/new.eaf'],
      modified: ['elan_files/a.eaf', 'elan_files/b.eaf'],
      deleted: ['elan_files/retired.eaf'],
    },
  };
}

function mountView({ locale = 'en', upload = contribution() } = {}) {
  return mount(UploadResolutionView, {
    props: { projectId: 1, projectName: 'corpus', upload },
    global: {
      plugins: [createI18n({ legacy: false, locale, messages: { en, fr } })],
      stubs: {
        'font-awesome-icon': true,
        'router-link': { template: '<a><slot /></a>' },
        ReviewCasePanel: true,
        ConflictMergeView: {
          name: 'ConflictMergeView',
          props: ['filename'],
          emits: ['loaded', 'open-review'],
          template: '<div class="comparison-stub">{{ filename }}</div>',
        },
      },
    },
  });
}

async function choose(wrapper, strategyTitle) {
  const option = wrapper
    .findAll('.strategy-option')
    .find((button) => button.text().includes(strategyTitle));
  await option.trigger('click');
}

describe('UploadResolutionView', () => {
  beforeEach(() => {
    adminCompleteMerge.mockReset().mockResolvedValue({ status: 'merged' });
  });

  it('says that other files, including deletions, are applied whichever outcome is chosen', async () => {
    const wrapper = mountView();

    await choose(wrapper, en.contributionResolution.choose.currentTitle);

    const text = wrapper.get('.decision-confirmation').text();
    expect(text).toContain(
      'Either way, 2 other file changes from this contribution are applied.'
    );
    expect(text).toContain('This includes deleting 1 file from the project.');
  });

  it('withholds the annotation impact until every overlapping file is compared', async () => {
    const wrapper = mountView();
    await choose(wrapper, en.contributionResolution.choose.incomingTitle);
    expect(wrapper.get('.partial-impact').text()).toContain(
      'Compared 0 of 2 overlapping files.'
    );

    const buttons = () => wrapper.findAll('.conflict-file-item button');
    await buttons()[0].trigger('click');
    wrapper.findComponent({ name: 'ConflictMergeView' }).vm.$emit('loaded', {
      filename: 'elan_files/a.eaf',
      review: { changes: [{ kinds: ['value_changed'] }] },
    });
    await flushPromises();
    expect(wrapper.get('.partial-impact').text()).toContain(
      'Compared 1 of 2 overlapping files.'
    );

    await buttons()[1].trigger('click');
    wrapper.findComponent({ name: 'ConflictMergeView' }).vm.$emit('loaded', {
      filename: 'elan_files/b.eaf',
      review: { changes: [{ kinds: ['value_changed'] }, { kinds: ['added'] }] },
    });
    await flushPromises();

    expect(wrapper.find('.partial-impact').exists()).toBe(false);
    expect(wrapper.get('.decision-impact').text()).toContain(
      'Apply 2 value changes and 1 addition.'
    );
  });

  it('cannot apply a decision acknowledged for a different contribution', async () => {
    const wrapper = mountView();
    await choose(wrapper, en.contributionResolution.choose.incomingTitle);
    await wrapper
      .get('.decision-confirmation input[type="checkbox"]')
      .setValue(true);
    expect(wrapper.get('.resolve-btn').attributes('disabled')).toBeUndefined();

    await wrapper.setProps({ upload: contribution(9) });

    expect(wrapper.find('.decision-confirmation').exists()).toBe(false);
    expect(wrapper.get('.resolve-btn').attributes('disabled')).toBeDefined();
  });

  it('completes the contribution with the acknowledged outcome', async () => {
    const wrapper = mountView();
    await choose(wrapper, en.contributionResolution.choose.currentTitle);
    await wrapper
      .get('.decision-confirmation input[type="checkbox"]')
      .setValue(true);

    await wrapper.get('.resolve-btn').trigger('click');
    await flushPromises();

    expect(adminCompleteMerge).toHaveBeenCalledWith(
      'corpus',
      'contribution-5_pending_approval',
      'accept_current'
    );
    expect(wrapper.emitted('resolved')).toEqual([[{ status: 'merged' }]]);
  });

  it('presents the decision in the administrator’s language', async () => {
    const wrapper = mountView({ locale: 'fr' });

    await choose(wrapper, fr.contributionResolution.choose.incomingTitle);

    expect(wrapper.text()).toContain(fr.contributionResolution.title);
    expect(wrapper.get('.decision-confirmation').text()).toContain(
      fr.contributionResolution.confirm.incomingConsequence
    );
    expect(wrapper.text()).not.toContain('Either way');
  });
});
