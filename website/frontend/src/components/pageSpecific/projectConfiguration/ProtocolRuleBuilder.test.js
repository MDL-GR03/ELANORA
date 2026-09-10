// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import ProtocolRuleBuilder from './ProtocolRuleBuilder.vue';

const emptyRules = () => ({
  required_tiers: [],
  tier_parents: {},
  tier_linguistic_types: {},
  required_controlled_vocabularies: [],
  media_required: false,
  allowed_media_mime_types: [],
});

describe('ProtocolRuleBuilder', () => {
  it('builds a required tier without exposing JSON editing', async () => {
    const wrapper = mount(ProtocolRuleBuilder, {
      props: { modelValue: emptyRules() },
      global: { stubs: { 'font-awesome-icon': true } },
    });

    await wrapper
      .get('input[placeholder="For example: Manual signs"]')
      .setValue('Manual signs');
    await wrapper.get('.add-tier > button').trigger('click');

    const update = wrapper.emitted('update:modelValue')[0][0];
    expect(update.required_tiers).toEqual(['Manual signs']);
    expect(wrapper.find('textarea').exists()).toBe(false);
  });

  it('renders an existing parent relationship as a hierarchy', () => {
    const wrapper = mount(ProtocolRuleBuilder, {
      props: {
        modelValue: {
          ...emptyRules(),
          required_tiers: ['Hand repetition', 'Manual signs'],
          tier_parents: { 'Hand repetition': 'Manual signs' },
          tier_linguistic_types: {
            'Hand repetition': 'Manual_prominence_repetition',
          },
        },
      },
      global: { stubs: { 'font-awesome-icon': true } },
    });

    expect(wrapper.get('.hierarchy-preview').text()).toContain('Manual signs');
    expect(wrapper.get('.hierarchy-preview').text()).toContain(
      'Hand repetition'
    );
    expect(wrapper.get('.hierarchy-preview').text()).toContain(
      'Manual_prominence_repetition'
    );
  });
});
