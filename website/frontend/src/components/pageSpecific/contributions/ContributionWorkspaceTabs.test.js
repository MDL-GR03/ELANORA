// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import ContributionWorkspaceTabs from './ContributionWorkspaceTabs.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));

describe('ContributionWorkspaceTabs', () => {
  it('exposes queue and review counts and emits navigation choices', async () => {
    const wrapper = mount(ContributionWorkspaceTabs, {
      props: {
        activeView: 'queue',
        contributionCount: 3,
        activeReviewCount: 2,
        canAdminister: true,
      },
    });

    expect(
      wrapper.get('#contribution-queue-tab').attributes('aria-selected')
    ).toBe('true');
    expect(wrapper.get('#contribution-history-tab').exists()).toBe(true);
    await wrapper.get('#contribution-reviews-tab').trigger('click');
    expect(wrapper.emitted('select')).toEqual([['reviews']]);
  });

  it('supports arrow-key tab navigation and roving focus', async () => {
    const wrapper = mount(ContributionWorkspaceTabs, {
      attachTo: document.body,
      props: {
        activeView: 'queue',
        canAdminister: true,
      },
    });
    const queue = wrapper.get('#contribution-queue-tab');
    const reviews = wrapper.get('#contribution-reviews-tab');

    expect(queue.attributes('tabindex')).toBe('0');
    expect(reviews.attributes('tabindex')).toBe('-1');
    queue.element.focus();
    await queue.trigger('keydown', { key: 'ArrowRight' });

    expect(document.activeElement).toBe(reviews.element);
    expect(wrapper.emitted('select')).toEqual([['reviews']]);
    wrapper.unmount();
  });

  it('does not expose project history to non-administrators', () => {
    const wrapper = mount(ContributionWorkspaceTabs, {
      props: { activeView: 'queue', canAdminister: false },
    });

    expect(wrapper.find('#contribution-history-tab').exists()).toBe(false);
  });
});
