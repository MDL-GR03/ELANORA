// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import CorpusProtocolSuggestion from './CorpusProtocolSuggestion.vue';
import AppSelect from '@/components/common/AppSelect.vue';

const suggestion = {
  total_files: 2,
  analyzed_files: 2,
  skipped_files: [],
  files_with_media: 2,
  media_type_counts: { 'video/mp4': 2 },
  proposed_rules: {},
  vocabulary_suggestions: [
    {
      vocabulary_id: 'greetings',
      occurrence_count: 2,
      coverage_percent: 100,
      suggested_required: true,
    },
  ],
  tier_suggestions: [
    {
      tier_id: 'utterance',
      occurrence_count: 2,
      coverage_percent: 100,
      suggested_required: true,
      parent_ref: null,
      parent_consistency_percent: null,
      parent_variants: {},
      linguistic_type_ref: 'utterance-type',
      linguistic_type_consistency_percent: 100,
      linguistic_type_variants: { 'utterance-type': 2 },
    },
    {
      tier_id: 'translation',
      occurrence_count: 2,
      coverage_percent: 100,
      suggested_required: true,
      parent_ref: 'utterance',
      parent_consistency_percent: 100,
      parent_variants: { utterance: 2 },
      linguistic_type_ref: 'translation-type',
      linguistic_type_consistency_percent: 100,
      linguistic_type_variants: { 'translation-type': 2 },
    },
  ],
};

describe('CorpusProtocolSuggestion', () => {
  it('turns selected, consistent corpus evidence into editable rules', async () => {
    const wrapper = mount(CorpusProtocolSuggestion, {
      props: { suggestion },
      global: { stubs: { 'font-awesome-icon': true } },
    });

    await wrapper.get('footer button').trigger('click');

    const rules = wrapper.emitted('apply')[0][0];
    expect(rules.required_tiers).toEqual(['utterance', 'translation']);
    expect(rules.tier_parents).toEqual({ translation: 'utterance' });
    expect(rules.tier_linguistic_types).toEqual({
      utterance: 'utterance-type',
      translation: 'translation-type',
    });
    expect(rules.required_controlled_vocabularies).toEqual(['greetings']);
    expect(rules.media_required).toBe(true);
  });

  it('shows common candidates when the corpus has no universal tier', () => {
    const mixedCorpus = {
      ...suggestion,
      tier_suggestions: suggestion.tier_suggestions.map((tier) => ({
        ...tier,
        occurrence_count: 1,
        coverage_percent: 50,
        suggested_required: false,
      })),
    };
    const wrapper = mount(CorpusProtocolSuggestion, {
      props: { suggestion: mixedCorpus },
      global: { stubs: { 'font-awesome-icon': true } },
    });

    expect(wrapper.getComponent(AppSelect).props('modelValue')).toBe('common');
    expect(wrapper.findAll('.candidate')).toHaveLength(2);
    expect(wrapper.text()).toContain('No single tier appears in every file');
  });
});
