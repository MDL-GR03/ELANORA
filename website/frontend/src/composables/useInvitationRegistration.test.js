import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

import {
  EXISTING_ACCOUNT_REDIRECT_DELAY,
  addressPayload,
  useInvitationRegistration,
} from './useInvitationRegistration';

function createRegistration(overrides = {}) {
  const form = ref({
    firstName: 'Ada',
    lastName: 'Lovelace',
    username: 'ada_l',
    email: 'ada@example.org',
    confirmEmail: 'ada@example.org',
    password: 'the quiet river bends west',
    confirmPassword: 'the quiet river bends west',
    phoneNumber: '',
    affiliation: 'University of London',
    department: 'Linguistics',
    address: {
      countryId: 'GB',
      cityName: 'London',
      streetName: 'Dorset Street',
      streetNumber: '12',
      postalCode: 'W1U 8AA',
      addressLine2: '',
    },
  });
  const countries = ref([{ country_id: 'GB', country_name: 'United Kingdom' }]);
  const validationErrors = ref({});
  const usernameAvailable = ref(true);
  const emailAvailable = ref(true);
  const invitationApi = {
    validateInvitation: vi.fn().mockResolvedValue({
      data: {
        valid: true,
        user_exists: false,
        invitation: { receiver_email: 'invited@example.org' },
      },
    }),
  };
  const authApi = {
    registerWithInvitation: vi
      .fn()
      .mockResolvedValue({ data: { requires_activation: true } }),
  };
  const eventMessages = { addMessage: vi.fn() };
  const router = { push: vi.fn() };
  const reportError = vi.fn();
  const registration = useInvitationRegistration({
    form,
    countries,
    translate: (key) => key,
    invitationApi,
    authApi,
    eventMessages,
    router,
    validateAllFields: vi.fn(),
    validationErrors,
    usernameAvailable,
    emailAvailable,
    reportError,
    ...overrides,
  });
  return {
    form,
    countries,
    validationErrors,
    usernameAvailable,
    emailAvailable,
    invitationApi,
    authApi,
    eventMessages,
    router,
    reportError,
    registration,
  };
}

describe('useInvitationRegistration', () => {
  it('fills in the invited address and refuses to let it be replaced', async () => {
    const { form, registration } = createRegistration();
    registration.invitationCode.value = 'CODE-1';
    await registration.validateInvitationCode();
    expect(registration.invitationValid.value).toBe(true);
    expect(form.value.email).toBe('invited@example.org');
    expect(form.value.confirmEmail).toBe('invited@example.org');
  });

  it('asks for a code before validating one', async () => {
    const { invitationApi, registration } = createRegistration();
    await registration.validateInvitationCode();
    expect(invitationApi.validateInvitation).not.toHaveBeenCalled();
    expect(registration.invitationError.value).toBe(
      'register.invitation_code_required'
    );
  });

  it('reports why an invitation was refused', async () => {
    const { invitationApi, registration } = createRegistration();
    invitationApi.validateInvitation.mockResolvedValue({
      data: { valid: false, message: 'this invitation expired' },
    });
    registration.invitationCode.value = 'CODE-1';
    await registration.validateInvitationCode();
    expect(registration.invitationValid.value).toBe(false);
    expect(registration.invitationError.value).toBe('this invitation expired');
  });

  it('sends someone who already has an account to sign in', async () => {
    vi.useFakeTimers();
    try {
      const { invitationApi, router, registration } = createRegistration();
      invitationApi.validateInvitation.mockResolvedValue({
        data: { valid: true, user_exists: true },
      });
      registration.invitationCode.value = 'CODE-1';
      await registration.validateInvitationCode();
      expect(registration.invitationValid.value).toBe(false);
      await vi.advanceTimersByTimeAsync(EXISTING_ACCOUNT_REDIRECT_DELAY);
      expect(router.push).toHaveBeenCalledWith({ name: 'LoginPage' });
    } finally {
      vi.useRealTimers();
    }
  });

  it('registers with the invitation code and the typed address', async () => {
    const { authApi, router, registration } = createRegistration();
    registration.invitationCode.value = 'CODE-1';
    await registration.register();
    expect(authApi.registerWithInvitation).toHaveBeenCalledWith(
      expect.objectContaining({
        invitation_code: 'CODE-1',
        username: 'ada_l',
        email: 'ada@example.org',
        phone_number: null,
        address: expect.objectContaining({
          city_name: 'London',
          country_code: 'GB',
          country_name: 'United Kingdom',
        }),
      })
    );
    expect(router.push).toHaveBeenCalledWith({
      name: 'EmailVerificationPage',
      query: { email: 'ada@example.org', freshCode: 'true' },
    });
    expect(registration.loading.value).toBe(false);
  });

  it('goes straight to sign-in when no verification is required', async () => {
    const { authApi, router, registration } = createRegistration();
    authApi.registerWithInvitation.mockResolvedValue({ data: {} });
    await registration.register();
    expect(router.push).toHaveBeenCalledWith({ name: 'LoginPage' });
  });

  it.each([
    [
      'a field that failed its rules',
      (context) => {
        context.validationErrors.value = {
          username: 'register.username_taken',
        };
      },
      'register.please_fix_errors',
    ],
    [
      'passwords that differ',
      (context) => {
        context.form.value.confirmPassword = 'Different1!';
      },
      'register.passwords_no_match',
    ],
    [
      'emails that differ',
      (context) => {
        context.form.value.confirmEmail = 'other@example.org';
      },
      'register.emails_no_match',
    ],
    [
      'a username already taken',
      (context) => {
        context.usernameAvailable.value = false;
      },
      'register.username_taken',
    ],
    [
      'an email already registered',
      (context) => {
        context.emailAvailable.value = false;
      },
      'register.email_taken',
    ],
  ])('refuses to submit with %s', async (_name, breakIt, expected) => {
    const context = createRegistration();
    breakIt(context);
    await context.registration.register();
    expect(context.authApi.registerWithInvitation).not.toHaveBeenCalled();
    expect(context.eventMessages.addMessage).toHaveBeenCalledWith(
      expected,
      'error'
    );
  });

  it('shows what the server said when registration fails', async () => {
    const { authApi, eventMessages, reportError, registration } =
      createRegistration();
    authApi.registerWithInvitation.mockRejectedValue({
      response: { data: { detail: 'this invitation was already used' } },
    });
    await registration.register();
    expect(eventMessages.addMessage).toHaveBeenCalledWith(
      'this invitation was already used',
      'error'
    );
    expect(reportError).toHaveBeenCalled();
    expect(registration.loading.value).toBe(false);
  });

  it('explains a password the server refused', async () => {
    const { authApi, eventMessages, registration } = createRegistration({
      translate: (key) => `t:${key}`,
    });
    authApi.registerWithInvitation.mockRejectedValue({
      response: {
        data: { detail: [{ type: 'password_common', loc: ['body'] }] },
      },
    });
    await registration.register();
    expect(eventMessages.addMessage).toHaveBeenCalledWith(
      't:passwordPolicy.errors.common',
      'error'
    );
  });

  it('omits an address that is not complete', () => {
    expect(addressPayload({ cityName: 'London' }, [])).toBeNull();
    expect(addressPayload(undefined, [])).toBeNull();
  });

  it('records an unknown country by its code alone', () => {
    expect(
      addressPayload(
        {
          streetName: 'Dorset Street',
          cityName: 'London',
          postalCode: 'W1U 8AA',
          countryId: 'GB',
        },
        []
      )
    ).toEqual({
      street_name: 'Dorset Street',
      street_number: null,
      city_name: 'London',
      country_code: 'GB',
      country_name: '',
      postal_code: 'W1U 8AA',
      address_line_2: null,
    });
  });
});
