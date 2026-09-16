// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { describe, expect, it } from 'vitest';
import { createI18n } from 'vue-i18n';

import messages from '@/locales/en.json';

const i18n = () =>
  createI18n({ legacy: false, locale: 'en', messages: { en: messages } });
import UserConfirm from './UserConfirm.vue';

describe('UserConfirm', () => {
  it('renders its semantic icon without relying on global app components', () => {
    const wrapper = mount(UserConfirm, {
      global: { plugins: [i18n()] },
      props: {
        modelValue: true,
        title: 'Mark this review as resolved?',
        message: 'No further action is required.',
        confirmText: 'Mark resolved',
      },
      attachTo: document.body,
    });

    expect(wrapper.get('.confirm-dialog').classes()).toContain('tone-success');
    expect(wrapper.find('.confirm-icon svg').exists()).toBe(true);
    expect(wrapper.find('.confirm-button.primary svg').exists()).toBe(true);
    wrapper.unmount();
  });

  it('uses unique accessible names and restores focus to its opener', async () => {
    const opener = document.createElement('button');
    document.body.append(opener);
    opener.focus();
    const wrapper = mount(UserConfirm, {
      global: { plugins: [i18n()] },
      props: {
        modelValue: true,
        title: 'Confirm action',
        message: 'This action needs confirmation.',
      },
      attachTo: document.body,
    });
    await nextTick();

    const dialog = wrapper.get('.confirm-dialog');
    expect(dialog.attributes('aria-labelledby')).toMatch(
      /^confirmation-title-/
    );
    expect(dialog.attributes('aria-describedby')).toMatch(
      /^confirmation-message-/
    );
    expect(document.activeElement).toBe(wrapper.get('.secondary').element);

    await wrapper.setProps({ modelValue: false });
    await nextTick();
    expect(document.activeElement).toBe(opener);

    wrapper.unmount();
    opener.remove();
  });
});
