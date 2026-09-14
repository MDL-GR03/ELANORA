// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import NamingStandardCreateForm from './NamingStandardCreateForm.vue';

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (key) => key }) }));

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const draft = () => ({
  name: '',
  description: '',
  project_file_type_id: '',
  components: [
    {
      name: 'prefix_EAF',
      regex: 'EAF',
      description: '',
      order: 1,
      accepted_values_str: '',
    },
  ],
});

const mountForm = (props = {}) =>
  mount(NamingStandardCreateForm, {
    props: {
      draft: draft(),
      commaPattern: 'session',
      exampleFilename: '',
      fileTypeOptions: [{ value: 7, label: 'ELAN (.eaf)' }],
      prefixValue: 'prefix_EAF',
      knownSeparators: ['_', '-'],
      exampleCommaPattern: 'session, _, speaker',
      extractionError: '',
      showAcceptedValuesWarning: false,
      unusualAcceptedValue: '',
      getAcceptedValuesPlaceholder: () => '001, 002',
      ...props,
    },
    global: {
      stubs: {
        AppSelect: {
          template:
            '<button class="file-type" type="button" @click="$emit(\'change\')">ELAN</button>',
        },
      },
    },
  });

describe('NamingStandardCreateForm', () => {
  it('presents the naming draft and emits workflow actions', async () => {
    const wrapper = mountForm();

    expect(wrapper.get('#standard-name').attributes('required')).toBeDefined();
    expect(
      wrapper.get('.configure-naming-prefix-box').attributes('readonly')
    ).toBeDefined();
    expect(wrapper.get('tbody input').attributes('readonly')).toBeDefined();

    await wrapper.get('.file-type').trigger('click');
    await wrapper.get('#pattern-comma-input').trigger('input');
    await wrapper.get('form').trigger('submit');
    await wrapper.get('button.cancel').trigger('click');

    expect(wrapper.emitted('file-type-change')).toHaveLength(1);
    expect(wrapper.emitted('pattern-input')).toHaveLength(1);
    expect(wrapper.emitted('submit')).toHaveLength(1);
    expect(wrapper.emitted('cancel')).toHaveLength(1);
  });

  it('surfaces extraction errors and blocks submission', () => {
    const wrapper = mountForm({ extractionError: 'Pattern does not match' });

    expect(wrapper.get('.configure-naming-error').text()).toBe(
      'Pattern does not match'
    );
    expect(
      wrapper.get('button[type="submit"]').attributes('disabled')
    ).toBeDefined();
  });

  it('shows accepted-value guidance and delegates component edits', async () => {
    const wrapper = mountForm({
      showAcceptedValuesWarning: true,
      unusualAcceptedValue: 'A B',
    });

    expect(wrapper.find('.configure-naming-warning').exists()).toBe(true);
    const acceptedValues = wrapper.findAll('tbody input')[3];
    expect(acceptedValues.attributes('placeholder')).toBe('001, 002');
    await acceptedValues.trigger('input');
    expect(wrapper.emitted('accepted-values-input')).toHaveLength(1);
  });
});
