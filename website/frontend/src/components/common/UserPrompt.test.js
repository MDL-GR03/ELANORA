// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { describe, expect, it } from 'vitest';

import UserPrompt from './UserPrompt.vue';

describe('UserPrompt', () => {
  it('focuses the input, exposes unique relationships, and restores focus', async () => {
    const opener = document.createElement('button');
    document.body.append(opener);
    opener.focus();
    const wrapper = mount(UserPrompt, {
      attachTo: document.body,
      props: {
        modelValue: true,
        message: 'Number of components',
        title: 'Choose a component count',
      },
    });
    await nextTick();

    const dialog = wrapper.get('[role="dialog"]');
    const input = wrapper.get('input');
    expect(dialog.attributes('aria-labelledby')).toMatch(/^prompt-title-/);
    expect(input.attributes('id')).toMatch(/^user-prompt-value-/);
    expect(document.activeElement).toBe(input.element);

    await wrapper.setProps({ modelValue: false });
    await nextTick();
    expect(document.activeElement).toBe(opener);
    wrapper.unmount();
    opener.remove();
  });

  it('announces validation and blocks invalid submission', async () => {
    const wrapper = mount(UserPrompt, {
      props: {
        modelValue: true,
        message: 'Number of components',
        defaultValue: 0,
        validator: (value) => (Number(value) > 0 ? '' : 'Use at least one.'),
      },
    });
    await nextTick();

    const input = wrapper.get('input');
    const warning = wrapper.get('[role="alert"]');
    expect(input.attributes('aria-invalid')).toBe('true');
    expect(input.attributes('aria-describedby')).toBe(warning.attributes('id'));
    await wrapper.get('form').trigger('submit');
    expect(wrapper.emitted('submit')).toBeUndefined();

    await input.setValue('2');
    await wrapper.get('form').trigger('submit');
    expect(wrapper.emitted('submit')).toEqual([['2']]);
  });
});
