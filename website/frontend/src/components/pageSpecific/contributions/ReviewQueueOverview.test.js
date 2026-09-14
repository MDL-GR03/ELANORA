// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import ReviewQueueOverview from './ReviewQueueOverview.vue';

const global = {
  stubs: { 'font-awesome-icon': { template: '<span />' } },
};

describe('ReviewQueueOverview', () => {
  it('summarizes active correction states', () => {
    const wrapper = mount(ReviewQueueOverview, {
      props: {
        casesCount: 6,
        activeCount: 4,
        changesRequestedCount: 2,
        resubmittedCount: 1,
        activeCasesCount: 4,
      },
      global,
    });

    expect(wrapper.get('.review-summary').text()).toContain('4Active');
    expect(wrapper.get('.review-summary').text()).toContain(
      '2Awaiting corrections'
    );
    expect(wrapper.get('.review-summary').text()).toContain(
      '1Ready for another review'
    );
  });

  it('distinguishes an empty contribution review from archived project reviews', () => {
    const contribution = mount(ReviewQueueOverview, {
      props: { uploadId: 9 },
      global,
    });
    const project = mount(ReviewQueueOverview, {
      props: { closedCasesCount: 3 },
      global,
    });

    expect(contribution.get('.panel-state').text()).toContain(
      'this contribution'
    );
    expect(project.get('.panel-state').text()).toContain('no active');
  });

  it('emits normalized search and status filters for larger queues', async () => {
    const wrapper = mount(ReviewQueueOverview, {
      props: { activeCasesCount: 6, query: '', status: '' },
      global,
    });

    await wrapper.get('input[type="search"]').setValue('  gloss  ');
    await wrapper.get('.app-select-trigger').trigger('click');
    await wrapper.findAll('[role="option"]')[2].trigger('click');

    expect(wrapper.emitted('update:query')).toEqual([['gloss']]);
    expect(wrapper.emitted('update:status')).toEqual([['changes_requested']]);
  });

  it('gives load failures alert semantics', () => {
    const wrapper = mount(ReviewQueueOverview, {
      props: { error: 'Could not load reviews' },
      global,
    });

    expect(wrapper.get('[role="alert"]').text()).toBe('Could not load reviews');
  });
});
