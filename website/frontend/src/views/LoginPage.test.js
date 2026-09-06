// @vitest-environment jsdom

import { createPinia, setActivePinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { createMemoryHistory, createRouter } from 'vue-router';
import { beforeEach, describe, expect, it } from 'vitest';

import messages from '@/locales/en.json';
import { useAppInfoStore } from '@/stores/appInfo';
import { useUserStore } from '@/stores/user';
import LoginPage from './LoginPage.vue';

async function renderLoginPage() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const appInfo = useAppInfoStore();
  const user = useUserStore();
  appInfo.instance = {
    instance_name: 'LSFB instance',
    institution_name: 'Laboratoire LSFB',
  };
  user.authState.loading = false;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: LoginPage },
      { path: '/forgot-password', component: { template: '<div />' } },
      { path: '/register', component: { template: '<div />' } },
      { path: '/contact', component: { template: '<div />' } },
    ],
  });
  await router.push('/');
  await router.isReady();

  return mount(LoginPage, {
    global: {
      plugins: [
        pinia,
        router,
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
    },
  });
}

describe('LoginPage', () => {
  beforeEach(() => localStorage.clear());

  it('shows public institution data and an accessible credential form', async () => {
    const wrapper = await renderLoginPage();

    expect(wrapper.text()).toContain('LSFB instance');
    expect(wrapper.text()).toContain('Laboratoire LSFB');
    expect(wrapper.get('label[for="login"]').exists()).toBe(true);
    expect(wrapper.get('#login').attributes('autocomplete')).toBe('username');
    expect(wrapper.get('#password').attributes('autocomplete')).toBe(
      'current-password'
    );
  });

  it('does not offer unsupported remember-me, SSO, or fake statistics', async () => {
    const wrapper = await renderLoginPage();

    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain('Login with SSO');
    expect(wrapper.text()).not.toContain('Active projects');
  });
});
