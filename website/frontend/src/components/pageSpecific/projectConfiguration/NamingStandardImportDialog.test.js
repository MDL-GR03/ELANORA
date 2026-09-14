// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import NamingStandardImportDialog from './NamingStandardImportDialog.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));

const baseProps = {
  importStep: 1,
  selectedImportProject: null,
  importProjectOptions: [{ value: 20, label: 'Source project' }],
  importStandards: [],
  existingStandardKeys: new Set(),
  selectedStandardIds: [],
  targetFileTypeKeys: new Set(),
  getSourceFileTypeDisplay: () => 'ELAN (.eaf)',
  buildExampleFilename: () => 'CORPUS_001.eaf',
  getPatternOrderedComponents: (standard) => standard.components || [],
  isStandardFolded: () => true,
};

const mountDialog = (props = {}, options = {}) =>
  mount(NamingStandardImportDialog, {
    props: { ...baseProps, ...props },
    ...(options.attachTo ? { attachTo: options.attachTo } : {}),
    global: {
      stubs: {
        FontAwesomeIcon: true,
        AppSelect: {
          props: ['modelValue'],
          template:
            '<button class="select-source" @click="$emit(\'update:modelValue\', 20)">Select source</button>',
        },
      },
    },
  });

describe('NamingStandardImportDialog', () => {
  it('presents an accessible project step and closes from its backdrop', async () => {
    const wrapper = mountDialog();

    expect(wrapper.get('[role="dialog"]').attributes('aria-modal')).toBe(
      'true'
    );
    expect(wrapper.find('.import-modal-footer').exists()).toBe(false);
    expect(wrapper.get('.primary-action').attributes()).toHaveProperty(
      'disabled'
    );

    await wrapper.get('.select-source').trigger('click');
    expect(wrapper.emitted('update:selectedImportProject')).toEqual([[20]]);
    await wrapper.get('.import-modal-overlay').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(1);
  });

  it('filters stable duplicates and prevents selection without a target file type', () => {
    const wrapper = mountDialog({
      importStep: 2,
      importStandards: [
        {
          id: 1,
          name: 'Existing',
          file_type_id: 5,
          file_type_name: 'ELAN',
          project_file_type_id: 201,
        },
        {
          id: 2,
          name: 'Needs type',
          file_type_id: 8,
          file_type_name: 'CSV',
          project_file_type_id: 202,
        },
      ],
      existingStandardKeys: new Set(['Existing::5']),
      targetFileTypeKeys: new Set(['5:ELAN']),
    });

    expect(wrapper.text()).not.toContain('Existing');
    expect(wrapper.text()).toContain('Needs type');
    expect(wrapper.get('input[type="checkbox"]').attributes()).toHaveProperty(
      'disabled'
    );
    expect(wrapper.find('.secondary-action').exists()).toBe(true);
  });

  it('emits immutable selection updates and the final import action', async () => {
    const wrapper = mountDialog({
      importStep: 2,
      importStandards: [
        {
          id: 3,
          name: 'Reusable',
          file_type_id: 5,
          file_type_name: 'ELAN',
          project_file_type_id: 201,
          components: [],
        },
      ],
      targetFileTypeKeys: new Set(['5:ELAN']),
      selectedStandardIds: [],
    });

    await wrapper.get('input[type="checkbox"]').setValue(true);
    expect(wrapper.emitted('update:selectedStandardIds')).toEqual([[[3]]]);

    await wrapper.setProps({ selectedStandardIds: [3] });
    await wrapper.get('.import-modal-footer .primary-action').trigger('click');
    expect(wrapper.emitted('import-selected')).toHaveLength(1);
  });

  it('uses a keyboard-accessible disclosure for standard details', async () => {
    const wrapper = mountDialog({
      importStep: 2,
      importStandards: [
        {
          id: 3,
          name: 'Reusable',
          file_type_id: 5,
          file_type_name: 'ELAN',
          project_file_type_id: 201,
          components: [],
        },
      ],
      targetFileTypeKeys: new Set(['5:ELAN']),
    });
    const toggle = wrapper.get('.import-fold-toggle');

    expect(toggle.attributes('aria-expanded')).toBe('false');
    expect(toggle.attributes('aria-controls')).toBe(
      'import-standard-details-3'
    );
    await toggle.trigger('click');
    expect(wrapper.emitted('toggle-fold')).toEqual([[3]]);
    wrapper.unmount();
  });

  it('focuses its close control and returns focus when removed', async () => {
    const opener = document.createElement('button');
    document.body.append(opener);
    opener.focus();
    const wrapper = mountDialog({}, { attachTo: document.body });
    await wrapper.vm.$nextTick();

    expect(document.activeElement).toBe(
      wrapper.get('.import-modal-close').element
    );
    wrapper.unmount();
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });
});
