// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import AppSelect from '@/components/common/AppSelect.vue';
import { emptyRules } from '@/utils/protocolRules';
import ProtocolRuleBuilder from './ProtocolRuleBuilder.vue';

const render = (rules) =>
  mount(ProtocolRuleBuilder, {
    props: { modelValue: { ...emptyRules(), ...rules } },
    global: { stubs: { 'font-awesome-icon': true } },
  });
const lastUpdate = (wrapper) => wrapper.emitted('update:modelValue').at(-1)[0];
const selectById = (wrapper, id) =>
  wrapper
    .findAllComponents(AppSelect)
    .find((select) => select.props('id') === id);

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

  it('switches on a quality check for one tier', async () => {
    const wrapper = render({ required_tiers: ['utterance', 'gloss'] });

    await wrapper
      .get('input[aria-label="No empty values: gloss"]')
      .setValue(true);

    expect(lastUpdate(wrapper).non_empty_tiers).toEqual(['gloss']);
  });

  it('records a required content language for a tier', async () => {
    const wrapper = render({ required_tiers: ['translation'] });

    await wrapper
      .get('input[aria-label="Content language of translation"]')
      .setValue(' fr ');

    expect(lastUpdate(wrapper).tier_languages).toEqual({ translation: 'fr' });
  });

  it('removes a tier from its quality checks so the draft stays valid', async () => {
    const wrapper = render({
      required_tiers: ['utterance', 'gloss'],
      non_empty_tiers: ['gloss', 'utterance'],
      tier_languages: { gloss: 'en' },
    });

    await wrapper
      .get('button[aria-label="Remove required tier gloss"]')
      .trigger('click');

    const update = lastUpdate(wrapper);
    expect(update.required_tiers).toEqual(['utterance']);
    expect(update.non_empty_tiers).toEqual(['utterance']);
    expect(update.tier_languages).toEqual({});
  });

  it('requires vocabulary values in the languages typed', async () => {
    const wrapper = render({ required_controlled_vocabularies: ['greetings'] });

    await wrapper
      .get('input[placeholder="Any, or for example: en, fr"]')
      .setValue('fr, en');

    expect(lastUpdate(wrapper).vocabulary_languages).toEqual({
      greetings: ['en', 'fr'],
    });
  });

  it('adds a linguistic type constraint rule', async () => {
    const wrapper = render({});

    await wrapper
      .get('input[placeholder="For example: gloss-type"]')
      .setValue('gloss-type');
    selectById(wrapper, 'new-protocol-constraint').vm.$emit(
      'update:modelValue',
      'Symbolic_Subdivision'
    );
    await wrapper.vm.$nextTick();
    await wrapper.get('.add-constraint > button').trigger('click');

    expect(lastUpdate(wrapper).linguistic_type_constraints).toEqual({
      'gloss-type': 'Symbolic_Subdivision',
    });
  });

  it('offers enforcement only for configured rules and records warnings', async () => {
    const wrapper = render({
      required_tiers: ['utterance'],
      non_empty_tiers: ['utterance'],
    });

    const labels = wrapper
      .findAll('.severities li > span')
      .map((item) => item.text());
    expect(labels).toEqual(['Required tiers', 'No empty values']);

    selectById(wrapper, 'protocol-severity-non_empty_tiers').vm.$emit(
      'change',
      'warning'
    );
    await wrapper.vm.$nextTick();

    expect(lastUpdate(wrapper).severities).toEqual({
      non_empty_tiers: 'warning',
    });
  });

  it('shows a frozen filename standard and can remove it', async () => {
    const wrapper = render({
      filename_standard: {
        name: 'Session files',
        pattern: 'session-{number}',
        components: [
          { name: 'number', regex: '[0-9]{3}', accepted_values: ['001-099'] },
        ],
      },
    });

    const panel = wrapper.get('.filename-standard');
    expect(panel.text()).toContain('session-{number}');
    expect(panel.text()).toContain('Accepted: 001-099');

    await panel.get('.remove-button').trigger('click');

    expect(lastUpdate(wrapper).filename_standard).toBeNull();
  });
});
