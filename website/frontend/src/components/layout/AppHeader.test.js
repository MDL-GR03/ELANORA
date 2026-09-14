// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import AppHeader from './AppHeader.vue';

vi.mock('vue-router', () => ({
  useRoute: () => ({ fullPath: '/contribution' }),
}));
vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (value) => value }),
}));
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ isAuthenticated: true, user: {} }),
}));
vi.mock('@/stores/appInfo', () => ({
  useAppInfoStore: () => ({ instance: {} }),
}));
vi.mock('@/stores/project', () => ({
  useProjectStore: () => ({ currentProject: null }),
}));
vi.mock('@/utils/authorization', () => ({
  hasProjectPermission: () => true,
}));

describe('AppHeader mobile navigation', () => {
  it('closes when its outside backdrop is clicked', async () => {
    const wrapper = mount(AppHeader, {
      global: {
        stubs: {
          'font-awesome-icon': true,
          RouterLink: { template: '<a><slot /></a>' },
          InstanceSection: true,
          ProjectSection: true,
          NotificationBell: true,
        },
        mocks: { $t: (value) => value },
      },
    });

    await wrapper.get('.mobile-menu-button').trigger('click');
    expect(wrapper.get('#primary-navigation').classes()).toContain('open');
    await wrapper.get('.mobile-menu-backdrop').trigger('click');
    expect(wrapper.find('.mobile-menu-backdrop').exists()).toBe(false);
    expect(wrapper.get('#primary-navigation').classes()).not.toContain('open');
  });

  it('closes with Escape and restores focus to the menu button', async () => {
    const wrapper = mount(AppHeader, {
      attachTo: document.body,
      global: {
        stubs: {
          'font-awesome-icon': true,
          RouterLink: { template: '<a><slot /></a>' },
          InstanceSection: true,
          ProjectSection: true,
          NotificationBell: true,
        },
        mocks: { $t: (value) => value },
      },
    });
    const button = wrapper.get('.mobile-menu-button');

    await button.trigger('click');
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    await wrapper.vm.$nextTick();

    expect(wrapper.get('#primary-navigation').classes()).not.toContain('open');
    expect(document.activeElement).toBe(button.element);
    wrapper.unmount();
  });
});
