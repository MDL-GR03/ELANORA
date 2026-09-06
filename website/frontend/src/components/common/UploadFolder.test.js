// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import en from '@/locales/en.json';
import UploadFolder from './UploadFolder.vue';

function mountUploader(props = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } });

  return mount(UploadFolder, {
    props,
    global: {
      plugins: [pinia, i18n],
      stubs: { FontAwesomeIcon: true },
    },
  });
}

describe('UploadFolder', () => {
  beforeEach(() => {
    vi.stubGlobal('requestAnimationFrame', (callback) => callback());
  });

  it('offers keyboard-operable file and folder selectors', async () => {
    const wrapper = mountUploader();
    const buttons = wrapper.findAll('.upload-browse-actions button');
    const inputs = wrapper.findAll('input[type="file"]');
    const fileClick = vi.spyOn(inputs[0].element, 'click');
    const folderClick = vi.spyOn(inputs[1].element, 'click');

    await buttons[0].trigger('click');
    await buttons[1].trigger('click');

    expect(fileClick).toHaveBeenCalledOnce();
    expect(folderClick).toHaveBeenCalledOnce();
    expect(inputs[1].attributes()).toHaveProperty('webkitdirectory');
  });

  it('keeps valid EAF files while reporting skipped formats', async () => {
    const wrapper = mountUploader();
    const valid = new File(['<ANNOTATION_DOCUMENT />'], 'study.eaf', {
      type: 'application/xml',
    });
    const invalid = new File(['notes'], 'notes.txt', { type: 'text/plain' });

    wrapper.vm.addFiles([invalid, valid]);
    await wrapper.vm.$nextTick();

    const updates = wrapper.emitted('update:modelValue');
    expect(updates).toHaveLength(1);
    expect(updates[0][0]).toEqual([valid]);
    expect(wrapper.text()).toContain('study.eaf');
  });

  it('rejects an oversized EAF file without mutating the selection', () => {
    const wrapper = mountUploader({ maxFileSize: 4 });
    const oversized = new File(['12345'], 'too-large.eaf');

    wrapper.vm.addFiles([oversized]);

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    expect(wrapper.emitted('error')?.[0]?.[0]).toContain('too-large.eaf');
  });

  it('prevents selection changes while the control is disabled', async () => {
    const wrapper = mountUploader({
      modelValue: [new File(['ok'], 'existing.eaf')],
      disabled: true,
    });

    await wrapper.get('.remove-btn').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    expect(wrapper.get('.remove-btn').attributes('disabled')).toBeDefined();
  });
});
