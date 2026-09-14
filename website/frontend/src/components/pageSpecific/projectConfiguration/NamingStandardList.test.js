// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import NamingStandardList from './NamingStandardList.vue';

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (key) => key }) }));

const standard = {
  id: 1,
  name: 'Corpus naming',
  description: 'Shared session convention',
  project_file_type_id: 10,
  pattern: '{prefix_ELAN}_{session}',
  components: [
    {
      name: 'session',
      regex: '\\p{N}{3}',
      accepted_values: [{ value: '001' }, '002'],
    },
  ],
};

const mountList = (props = {}) =>
  mount(NamingStandardList, {
    props: {
      standards: [standard],
      openStandardId: null,
      getFileTypeDisplay: () => 'ELAN (.eaf)',
      buildExampleFilename: () => 'CORPUS_001.eaf',
      getPatternOrderedComponents: (item) => item.components,
      getExampleValuesForStandard: () => ({ session: '001' }),
      ...props,
    },
    global: { stubs: { FontAwesomeIcon: true } },
  });

describe('NamingStandardList', () => {
  it('uses a real disclosure control for each collapsed standard', async () => {
    const wrapper = mountList();
    const disclosure = wrapper.get('.standard-heading');

    expect(disclosure.attributes('aria-expanded')).toBe('false');
    expect(wrapper.find('.standard-body').exists()).toBe(false);
    await disclosure.trigger('click');
    expect(wrapper.emitted('toggle')).toEqual([[1]]);
  });

  it('shows readable component evidence and emits deletion explicitly', async () => {
    const wrapper = mountList({ openStandardId: 1 });

    expect(wrapper.text()).toContain('CORPUS_001.eaf');
    expect(wrapper.text()).toContain('001, 002');
    expect(wrapper.get('.table-wrap table').exists()).toBe(true);
    await wrapper.get('.delete').trigger('click');
    expect(wrapper.emitted('delete')).toEqual([[1]]);
  });
});
