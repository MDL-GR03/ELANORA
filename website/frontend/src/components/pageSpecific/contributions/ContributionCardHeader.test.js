// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import ContributionCardHeader from './ContributionCardHeader.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));

const global = {
  stubs: { 'font-awesome-icon': { template: '<span />' } },
};

function mountHeader(upload, props = {}) {
  return mount(ContributionCardHeader, {
    props: { upload, canAdminister: true, ...props },
    global,
  });
}

describe('ContributionCardHeader', () => {
  it('offers merge, correction, test, and decline for ready work', async () => {
    const wrapper = mountHeader({
      upload_id: 18,
      merge_status: 'ready_to_merge',
      files: { modified: ['session.eaf'] },
      uploaded_at: '2026-09-09T22:48:47Z',
      uploaded_by: 'researcher',
    });

    expect(wrapper.find('.merge-btn').exists()).toBe(true);
    expect(wrapper.find('.review-btn').exists()).toBe(true);
    expect(wrapper.find('.resolve-btn').exists()).toBe(false);
    await wrapper.get('.merge-btn').trigger('click');
    await wrapper.get('.test-btn').trigger('click');
    await wrapper.get('.decline-btn').trigger('click');
    expect(wrapper.emitted('merge')).toHaveLength(1);
    expect(wrapper.emitted('test')).toHaveLength(1);
    expect(wrapper.emitted('decline')).toHaveLength(1);
  });

  it('only offers duplicate dismissal for a duplicate submission', () => {
    const wrapper = mountHeader({
      upload_id: 19,
      merge_status: 'duplicate',
      files: { modified: ['session.eaf'] },
    });

    expect(wrapper.find('.dismiss-btn').exists()).toBe(true);
    expect(wrapper.find('.merge-btn').exists()).toBe(false);
    expect(wrapper.find('.review-btn').exists()).toBe(false);
    expect(wrapper.find('.contribution-more-actions').exists()).toBe(false);
  });

  it('hides administrator decisions from contributors', () => {
    const wrapper = mountHeader(
      {
        upload_id: 20,
        merge_status: 'ready_to_merge',
        files: { new: ['new-session.eaf'] },
      },
      { canAdminister: false }
    );

    expect(wrapper.find('.view-btn').exists()).toBe(true);
    expect(wrapper.find('.merge-btn').exists()).toBe(false);
    expect(wrapper.find('.review-btn').exists()).toBe(false);
  });

  it('links an active discussion without offering a second correction request', () => {
    const wrapper = mountHeader({
      upload_id: 21,
      merge_status: 'changes_requested',
      files: { modified: ['session.eaf'] },
      review_case: { state: 'changes_requested' },
    });

    expect(wrapper.find('.review-link-btn').exists()).toBe(true);
    expect(wrapper.find('.review-btn').exists()).toBe(false);
  });
});
