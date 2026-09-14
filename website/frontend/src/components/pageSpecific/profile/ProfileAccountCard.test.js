// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ProfileAccountCard from './ProfileAccountCard.vue';

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (key) => key }) }));

const profile = {
  created_at: '2025-01-02T10:00:00Z',
  updated_at: '2025-03-04T10:00:00Z',
  last_login: '2025-05-06T10:00:00Z',
  is_active: true,
};

describe('ProfileAccountCard', () => {
  it('shows account dates, optional last login, and active status', () => {
    const wrapper = mount(ProfileAccountCard, {
      props: { userProfile: profile },
    });

    expect(wrapper.text()).toContain('2 janvier 2025');
    expect(wrapper.text()).toContain('4 mars 2025');
    expect(wrapper.text()).toContain('6 mai 2025');
    expect(wrapper.text()).toContain('profile.overview.account_info.active');
    expect(wrapper.get('.modern-status-badge').classes()).toContain('active');
  });

  it('omits last login and marks an inactive account', () => {
    const wrapper = mount(ProfileAccountCard, {
      props: {
        userProfile: { ...profile, last_login: null, is_active: false },
      },
    });

    expect(wrapper.text()).not.toContain(
      'profile.overview.account_info.last_login'
    );
    expect(wrapper.text()).toContain('profile.overview.account_info.inactive');
    expect(wrapper.get('.modern-status-badge').classes()).toContain('inactive');
  });
});
