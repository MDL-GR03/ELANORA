// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';

import NotificationBell from './NotificationBell.vue';

const notificationStore = {
  unreadNotifications: [
    {
      notification_id: 7,
      title: 'Contribution ready',
      message: 'A contribution is ready to review.',
      created_at: '2026-09-09T12:00:00Z',
      is_read: false,
      action_url: '/contribution',
    },
  ],
  unreadCount: 1,
  hasUnreadNotifications: true,
  loading: false,
  fetchUnreadNotifications: vi.fn().mockResolvedValue(undefined),
  fetchNotificationStats: vi.fn().mockResolvedValue(undefined),
  markNotificationAsRead: vi.fn().mockResolvedValue(undefined),
  markAllNotificationsAsRead: vi.fn().mockResolvedValue(undefined),
  deleteNotification: vi.fn().mockResolvedValue(undefined),
};

vi.mock('@/stores/notification', () => ({
  useNotificationStore: () => notificationStore,
}));
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, values) => (values?.count ? `${key} ${values.count}` : key),
  }),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe('NotificationBell', () => {
  it('connects its trigger to the panel and restores focus on Escape', async () => {
    const wrapper = mount(NotificationBell, {
      attachTo: document.body,
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    });
    await flushPromises();
    const trigger = wrapper.get('.notification-bell > button');

    expect(trigger.attributes('aria-expanded')).toBe('false');
    await trigger.trigger('click');
    await flushPromises();

    const panel = wrapper.get('[role="dialog"]');
    expect(trigger.attributes('aria-expanded')).toBe('true');
    expect(trigger.attributes('aria-controls')).toBe(panel.attributes('id'));
    expect(panel.attributes('aria-labelledby')).toMatch(
      /^notifications-heading-/
    );
    expect(document.activeElement).toBe(
      wrapper.get('.notification-close').element
    );

    await panel.trigger('keydown', { key: 'Escape' });
    await flushPromises();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(document.activeElement).toBe(trigger.element);
    wrapper.unmount();
  });

  it('gives icon-only notification actions accessible names', async () => {
    const wrapper = mount(NotificationBell, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    });
    await wrapper.get('.notification-bell > button').trigger('click');
    await flushPromises();

    expect(
      wrapper
        .get('[title="notificationBell.mark_as_read"]')
        .attributes('aria-label')
    ).toBe('notificationBell.mark_as_read');
    expect(
      wrapper.get('[title="notificationBell.delete"]').attributes('aria-label')
    ).toBe('notificationBell.delete');
    wrapper.unmount();
  });
});
