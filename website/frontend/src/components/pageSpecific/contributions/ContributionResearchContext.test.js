// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import ContributionResearchContext from './ContributionResearchContext.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));

const global = {
  stubs: { 'font-awesome-icon': { template: '<span />' } },
};

describe('ContributionResearchContext', () => {
  it('distinguishes topic, baseline correction, and out-of-scope tiers', () => {
    const wrapper = mount(ContributionResearchContext, {
      props: {
        context: {
          scope_status: 'outside_scope',
          declared_topic_name: 'Prosody',
          summary: 'Corrected prominence labels',
          changed_tiers: ['prosody', 'sign-left', 'translation'],
          baseline_changed_tiers: ['sign-left'],
          declared_baseline_correction_tiers: ['sign-left'],
          outside_scope_tiers: ['translation'],
        },
      },
      global,
    });

    const tiers = wrapper.findAll('.research-tier-list > span');
    expect(tiers[0].classes()).toEqual([]);
    expect(tiers[1].classes()).toContain('is-baseline-correction');
    expect(tiers[2].classes()).toContain('is-outside-scope');
    expect(tiers[2].attributes('title')).toBe(
      'contributionDetails.tiers.outside'
    );
    expect(wrapper.text()).toContain('Corrected prominence labels');
  });

  it('keeps a proposed topic explicit and emits administrator decisions', async () => {
    const wrapper = mount(ContributionResearchContext, {
      props: {
        context: {
          scope_status: 'topic_review_needed',
          proposed_topic_name: 'Interactional rhythm',
          changed_tiers: ['CA:summary1'],
        },
        topicOptions: [{ value: 7, label: 'Prosody' }],
        topicDecision: '',
        suggestionName: '',
        canAdminister: true,
        expanded: true,
      },
      global,
    });

    await wrapper.get('.app-select-trigger').trigger('click');
    await wrapper.get('[role="option"]').trigger('click');
    await wrapper.get('.research-topic-decision input').setValue('Rhythm');
    await wrapper.get('.research-topic-review-toggle').trigger('click');

    expect(wrapper.emitted('update:topicDecision')).toEqual([[7]]);
    expect(wrapper.emitted('update:suggestionName')).toEqual([['Rhythm']]);
    expect(wrapper.emitted('toggle')).toHaveLength(1);
  });

  it('does not expose topic controls to a researcher', () => {
    const wrapper = mount(ContributionResearchContext, {
      props: {
        context: { scope_status: 'topic_review_needed' },
        canAdminister: false,
        expanded: true,
      },
      global,
    });

    expect(wrapper.find('.research-topic-decision').exists()).toBe(false);
  });
});
