// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UserConfirm from './UserConfirm.vue';

describe('UserConfirm', () => {
  it('renders its semantic icon without relying on global app components', () => {
    const wrapper = mount(UserConfirm, {
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
});
