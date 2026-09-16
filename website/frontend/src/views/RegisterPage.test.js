// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { useEventMessageStore } from '@stores/eventMessage';
import RegisterPage from './RegisterPage.vue';

const validateInvitation = vi.fn();
const registerWithInvitation = vi.fn();
const getCountries = vi.fn();
const checkUsernameAvailability = vi.fn();
const checkEmailAvailability = vi.fn();
const push = vi.fn();

vi.mock('@/api/service/invitationService', () => ({
  validateInvitation: (...args) => validateInvitation(...args),
}));
vi.mock('@/api/service/authService', () => ({
  registerWithInvitation: (...args) => registerWithInvitation(...args),
}));
vi.mock('@/api/service/userService', () => ({
  checkUsernameAvailability: (...args) => checkUsernameAvailability(...args),
  checkEmailAvailability: (...args) => checkEmailAvailability(...args),
}));
vi.mock('@/api/service/locationService', () => ({
  getCountries: (...args) => getCountries(...args),
  validateCity: vi.fn(),
  validatePostalCode: vi.fn(),
  validatePostalCodeInCity: vi.fn(),
  validateStreetInCity: vi.fn(),
}));
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ query: {} }),
}));

function mountPage() {
  return mount(RegisterPage, {
    global: {
      plugins: [
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
      stubs: { FontAwesomeIcon: true, RouterLink: true },
    },
  });
}

async function acceptInvitation(wrapper, invitation = {}) {
  await wrapper.find('#invitation-code').setValue('CODE-1');
  await flushPromises();
  return invitation;
}

describe('RegisterPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    getCountries.mockResolvedValue({
      success: true,
      data: [{ country_id: 'FR', country_name: 'France' }],
    });
    validateInvitation.mockResolvedValue({
      data: {
        valid: true,
        user_exists: false,
        invitation: {
          receiver_email: 'invited@example.org',
          sender_username: 'coordinator',
        },
      },
    });
  });

  it('asks for an invitation code before showing the form', async () => {
    const wrapper = mountPage();
    await flushPromises();
    expect(wrapper.find('#invitation-code').exists()).toBe(true);
    expect(wrapper.find('form.register-form').exists()).toBe(false);
  });

  it('shows the whole form once the invitation is accepted', async () => {
    const wrapper = mountPage();
    await acceptInvitation(wrapper);

    expect(wrapper.find('form.register-form').exists()).toBe(true);
    for (const field of [
      '#first-name',
      '#last-name',
      '#username',
      '#password',
      '#confirm-password',
      '#email',
      '#confirm-email',
      '#affiliation',
      '#department',
      '#streetName',
      '#postalCode',
    ]) {
      expect(wrapper.find(field).exists()).toBe(true);
    }
    expect(wrapper.text()).toContain('coordinator');
  });

  it('fixes the email to the invited address', async () => {
    const wrapper = mountPage();
    await acceptInvitation(wrapper);

    const email = wrapper.find('#email');
    expect(email.element.value).toBe('invited@example.org');
    expect(email.attributes('disabled')).toBeDefined();
    expect(wrapper.find('#confirm-email').element.value).toBe(
      'invited@example.org'
    );
  });

  it('shows a field rule in the reader language and links it to the field', async () => {
    const wrapper = mountPage();
    await acceptInvitation(wrapper);

    const firstName = wrapper.find('#first-name');
    await firstName.setValue('A');
    await firstName.trigger('blur');

    expect(wrapper.text()).toContain(messages.register.first_name_too_short);
    expect(firstName.attributes('aria-invalid')).toBe('true');
    expect(firstName.attributes('aria-describedby')).toBe('first-name-message');
    expect(wrapper.find('#first-name-message [role="alert"]').exists()).toBe(
      true
    );
  });

  it('keeps registration out of reach until the form is complete', async () => {
    const wrapper = mountPage();
    await acceptInvitation(wrapper);

    const submit = wrapper.find('button[type="submit"]');
    expect(submit.attributes('disabled')).toBeDefined();
    await wrapper.find('form.register-form').trigger('submit');
    expect(registerWithInvitation).not.toHaveBeenCalled();
  });

  it('reports the password requirements it is holding out for', async () => {
    const wrapper = mountPage();
    await acceptInvitation(wrapper);

    const password = wrapper.find('#password');
    await password.trigger('focus');
    expect(wrapper.text()).toContain(
      messages.register.password_requirements_title
    );
    expect(wrapper.text()).toContain(
      messages.register.password_requirement_uppercase
    );

    await password.setValue('Analytical1!');
    expect(wrapper.text()).toContain(
      messages.register.password_strength_strong
    );
  });

  it('offers the countries the location service returned', async () => {
    const wrapper = mountPage();
    await acceptInvitation(wrapper);
    expect(getCountries).toHaveBeenCalled();
    await wrapper.find('#country').trigger('click');
    expect(wrapper.text()).toContain('France');
  });

  it('says so when the countries cannot be loaded', async () => {
    getCountries.mockResolvedValue({ success: false });
    mountPage();
    await flushPromises();
    expect(
      useEventMessageStore().messages.map((message) => message.translationKey)
    ).toContain(messages.register.error_loading_countries);
  });

  it('tells the researcher why an invitation was refused', async () => {
    validateInvitation.mockResolvedValue({
      data: { valid: false, message: 'This invitation has expired' },
    });
    const wrapper = mountPage();
    await acceptInvitation(wrapper);
    expect(wrapper.find('form.register-form').exists()).toBe(false);
    expect(wrapper.text()).toContain('This invitation has expired');
  });
});
