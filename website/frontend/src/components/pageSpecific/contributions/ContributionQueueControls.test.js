// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import ContributionQueueControls from './ContributionQueueControls.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key, values) => `${key}:${values?.count ?? ''}` }),
}));

const global = {
  stubs: { 'font-awesome-icon': { template: '<span />' } },
};

describe('ContributionQueueControls', () => {
  it('reports filter and normalized search changes', async () => {
    const wrapper = mount(ContributionQueueControls, {
      props: {
        filter: 'all',
        query: '',
        sort: 'oldest',
        total: 4,
        ready: 2,
        corrections: 1,
        conflicts: 1,
        resultCount: 4,
      },
      global,
    });

    await wrapper.findAll('.summary-card')[1].trigger('click');
    await wrapper.get('#incoming-work-search').setValue('  session.eaf  ');

    expect(wrapper.emitted('update:filter')).toEqual([['ready']]);
    expect(wrapper.emitted('update:query')).toEqual([['session.eaf']]);
    expect(wrapper.get('#incoming-work-search-count').text()).toContain('4');
  });

  it('passes ordering changes through its accessible select', async () => {
    const wrapper = mount(ContributionQueueControls, {
      props: {
        filter: 'all',
        query: '',
        sort: 'oldest',
        total: 1,
        ready: 1,
        corrections: 0,
        conflicts: 0,
        resultCount: 1,
      },
      global,
    });

    await wrapper.get('.app-select-trigger').trigger('click');
    await wrapper.findAll('[role="option"]')[1].trigger('click');
    expect(wrapper.emitted('update:sort')).toEqual([['newest']]);
  });
});
